import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, of } from 'rxjs';
import { catchError, tap } from 'rxjs/operators';
import { environment } from '../../environments/environment';

export interface ProductSpecification {
  name: string;
  description: string;
  features: string[];
  estimatedPrice: string;
  category: string;
}

export interface Message {
  role: string;
  content: string;
  timestamp: string;
}

// Interface for a single shopping option
export interface ShoppingOption {
  title: string;
  link: string;
  snippet: string;
}

export interface ChatResponse {
  conversation_id: string;
  response: string;
  productSpecification?: ProductSpecification;
  isSpecificationFinalized: boolean;
  messages: Message[];
  shoppingOptions?: ShoppingOption[];
}

export interface Conversation {
  conversation_id: string;
  messages: Message[];
}

@Injectable({
  providedIn: 'root',
})
export class AiService {
  private apiUrl = environment.apiUrl;
  private currentConversationId: string | null = null;
  private cachedMessages: Message[] = [];

  constructor(private http: HttpClient) {
    // Try to load conversation data from localStorage
    this.loadFromLocalStorage();
  }

  private loadFromLocalStorage(): void {
    this.currentConversationId = localStorage.getItem('currentConversationId');

    // Load cached messages if available
    const cachedMessagesJson = localStorage.getItem('cachedMessages');
    if (cachedMessagesJson) {
      try {
        this.cachedMessages = JSON.parse(cachedMessagesJson);
      } catch (error) {
        console.error('Error parsing cached messages:', error);
        this.cachedMessages = [];
      }
    }
  }

  private saveToLocalStorage(): void {
    if (this.currentConversationId) {
      localStorage.setItem('currentConversationId', this.currentConversationId);
    } else {
      localStorage.removeItem('currentConversationId');
    }

    // Only save messages if we have a valid structure (avoid saving partial/error states)
    if (
      this.cachedMessages &&
      Array.isArray(this.cachedMessages) &&
      this.cachedMessages.length > 0
    ) {
      // Ensure all messages have the required fields before saving
      const validMessages = this.cachedMessages.filter(
        (msg) => msg && msg.role && msg.content && msg.timestamp
      );
      if (validMessages.length === this.cachedMessages.length) {
        localStorage.setItem(
          'cachedMessages',
          JSON.stringify(this.cachedMessages)
        );
      } else {
        console.warn(
          'Attempted to save invalid message structure to localStorage. Skipping.'
        );
      }
    } else {
      localStorage.removeItem('cachedMessages'); // Clear cache if empty or invalid
    }
  }

  generateResponse(message: string): Observable<ChatResponse> {
    const payload = {
      message,
      conversation_id: this.currentConversationId,
      // Send cached messages as a fallback if server can't find the conversation
      // or if the server needs to reconstruct history
      cached_messages: this.cachedMessages,
    };

    return this.http
      .post<ChatResponse>(`${this.apiUrl}/api/chat`, payload)
      .pipe(
        tap((response) => {
          // Update conversation ID and cache the updated messages from the server response
          if (response.conversation_id) {
            this.currentConversationId = response.conversation_id;
          }
          if (response.messages && response.messages.length > 0) {
            this.cachedMessages = response.messages;
          } else {
            // If server didn't return messages (unexpected), clear cache
            this.cachedMessages = [];
          }
          this.saveToLocalStorage();
        }),
        catchError((error) => {
          console.error('Error in API call:', error);
          // Simple fallback: add an error message to the current local cache
          const errorTimestamp = new Date().toISOString();
          this.cachedMessages.push({
            role: 'user',
            content: message, // Keep the user message that failed
            timestamp: errorTimestamp,
          });
          this.cachedMessages.push({
            role: 'system',
            content:
              'Sorry, I encountered an error connecting to the server. Please try again later.',
            timestamp: errorTimestamp,
          });
          // We still need to return an Observable that conforms to ChatResponse
          // Create a minimal error response structure
          const errorResponse: ChatResponse = {
            conversation_id: this.currentConversationId || 'local-error',
            response: 'Error connecting to server.',
            isSpecificationFinalized: false,
            messages: this.cachedMessages, // Return the updated cache with error
            shoppingOptions: [], // Ensure this field exists
          };
          return of(errorResponse);
        })
      );
  }

  getConversation(conversationId: string): Observable<Conversation> {
    return this.http
      .get<Conversation>(`${this.apiUrl}/api/conversations/${conversationId}`)
      .pipe(
        tap((conversation) => {
          // Cache the retrieved messages
          if (conversation.messages && conversation.messages.length > 0) {
            this.currentConversationId = conversation.conversation_id;
            this.cachedMessages = conversation.messages;
            this.saveToLocalStorage();
          }
        }),
        catchError((error) => {
          console.error('Error retrieving conversation:', error);
          // If we have cached messages and they seem to match the ID, use them as fallback
          if (
            this.cachedMessages.length > 0 &&
            this.currentConversationId === conversationId
          ) {
            console.warn(
              `Falling back to cached messages for conversation ${conversationId}`
            );
            return of({
              conversation_id: conversationId,
              messages: this.cachedMessages,
            });
          }
          // If no cache match, rethrow or return an empty/error state
          throw error;
        })
      );
  }

  setCurrentConversation(conversationId: string): void {
    if (this.currentConversationId !== conversationId) {
      this.currentConversationId = conversationId;
      // Optionally clear messages when switching, or rely on getConversation to load
      // this.cachedMessages = [];
      this.saveToLocalStorage();
    }
  }

  startNewConversation(): void {
    this.currentConversationId = null;
    this.cachedMessages = [];
    this.saveToLocalStorage();
  }

  getCurrentConversationId(): string | null {
    return this.currentConversationId;
  }

  getCachedMessages(): Message[] {
    // Return a copy to prevent external modification
    return [...this.cachedMessages];
  }

  // This function is less reliable now that the server handles spec extraction
  // Kept for potential future client-side use, but primarily rely on server's productSpecification field
  extractProductSpecification(response: string): ProductSpecification | null {
    try {
      const jsonMatch = response.match(/```json\n([\s\S]*?)\n```/);
      if (jsonMatch && jsonMatch[1]) {
        return JSON.parse(jsonMatch[1]);
      }
      return null;
    } catch (error) {
      console.error('Error extracting product specification:', error);
      return null;
    }
  }
}
