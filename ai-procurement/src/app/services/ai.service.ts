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

export interface ChatResponse {
  conversation_id: string;
  response: string;
  productSpecification?: ProductSpecification;
  isSpecificationFinalized: boolean;
  messages: Message[];
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

    localStorage.setItem('cachedMessages', JSON.stringify(this.cachedMessages));
  }

  generateResponse(message: string): Observable<ChatResponse> {
    const payload = {
      message,
      conversation_id: this.currentConversationId,
      // Send cached messages as a fallback if server can't find the conversation
      cached_messages: this.cachedMessages,
    };

    return this.http
      .post<ChatResponse>(`${this.apiUrl}/api/chat`, payload)
      .pipe(
        tap((response) => {
          // Cache the updated messages
          if (response.messages && response.messages.length > 0) {
            this.cachedMessages = response.messages;
            this.saveToLocalStorage();
          }
        }),
        catchError((error) => {
          console.error('Error in API call:', error);
          // If we have cached messages, use them to form a basic response
          if (this.cachedMessages.length > 0) {
            return of({
              conversation_id: this.currentConversationId || 'local-fallback',
              response:
                'Sorry, I encountered an error connecting to the server. Using cached data to continue.',
              isSpecificationFinalized: false,
              messages: [
                ...this.cachedMessages,
                {
                  role: 'user',
                  content: message,
                  timestamp: new Date().toISOString(),
                },
                {
                  role: 'system',
                  content:
                    'Sorry, I encountered an error connecting to the server. Please try again later.',
                  timestamp: new Date().toISOString(),
                },
              ],
            } as ChatResponse);
          }
          throw error;
        })
      );
  }

  getConversation(conversationId: string): Observable<Conversation> {
    return this.http
      .get<Conversation>(`${this.apiUrl}/conversations/${conversationId}`)
      .pipe(
        tap((conversation) => {
          // Cache the retrieved messages
          if (conversation.messages && conversation.messages.length > 0) {
            this.cachedMessages = conversation.messages;
            this.saveToLocalStorage();
          }
        }),
        catchError((error) => {
          console.error('Error retrieving conversation:', error);
          // If we have cached messages and they match the conversation ID, use them
          if (
            this.cachedMessages.length > 0 &&
            this.currentConversationId === conversationId
          ) {
            return of({
              conversation_id: conversationId,
              messages: this.cachedMessages,
            });
          }
          throw error;
        })
      );
  }

  setCurrentConversation(conversationId: string): void {
    this.currentConversationId = conversationId;
    this.saveToLocalStorage();
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
    return this.cachedMessages;
  }

  extractProductSpecification(response: string): ProductSpecification | null {
    try {
      const jsonMatch = response.match(/```json\n([\s\S]*?)\n```/);
      if (jsonMatch) {
        return JSON.parse(jsonMatch[1]);
      }
      return null;
    } catch (error) {
      console.error('Error extracting product specification:', error);
      return null;
    }
  }
}
