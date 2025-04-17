import {
  Component,
  OnInit,
  ViewChild,
  ElementRef,
  AfterViewChecked,
  ChangeDetectorRef,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatListModule } from '@angular/material/list';
import { MatDividerModule } from '@angular/material/divider';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import {
  AiService,
  ProductSpecification,
  Message,
} from '../../services/ai.service';

@Component({
  selector: 'app-chat',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatCardModule,
    MatInputModule,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatListModule,
    MatDividerModule,
    MatSnackBarModule,
  ],
  templateUrl: './chat.component.html',
  styleUrl: './chat.component.scss',
})
export class ChatComponent implements OnInit, AfterViewChecked {
  @ViewChild('chatContainer') private chatContainer!: ElementRef;

  messages: Message[] = [];
  newMessage: string = '';
  loading: boolean = false;
  productSpecification: ProductSpecification | null = null;
  isSpecificationFinalized: boolean = false;
  conversationId: string | null = null;
  private shouldScroll: boolean = true;
  usingCachedData: boolean = false;

  constructor(
    private aiService: AiService,
    private changeDetectorRef: ChangeDetectorRef,
    private snackBar: MatSnackBar
  ) {}

  ngOnInit() {
    // Check for existing conversation
    const savedConversationId = this.aiService.getCurrentConversationId();
    if (savedConversationId) {
      this.conversationId = savedConversationId;
      this.loadConversation(savedConversationId);
    } else {
      // Check if there are cached messages without a conversation ID
      const cachedMessages = this.aiService.getCachedMessages();
      if (cachedMessages && cachedMessages.length > 0) {
        this.messages = cachedMessages;
        this.usingCachedData = true;
        this.showCachedDataNotification();
      } else {
        // Initialize with a welcome message for new conversations
        this.messages = [
          {
            role: 'system',
            content:
              'Hello! I am your AI Procurement Assistant. How can I help you today?',
            timestamp: new Date().toISOString(),
          },
        ];
      }
    }
  }

  ngAfterViewChecked() {
    if (this.shouldScroll) {
      this.scrollToBottom();
      this.shouldScroll = false;
    }
  }

  private scrollToBottom(): void {
    try {
      const element = this.chatContainer.nativeElement;
      element.scrollTop = element.scrollHeight;
    } catch (err) {
      console.error('Error scrolling to bottom:', err);
    }
  }

  loadConversation(conversationId: string): void {
    this.loading = true;
    this.aiService.getConversation(conversationId).subscribe(
      (conversation) => {
        this.messages = conversation.messages;
        this.conversationId = conversation.conversation_id;
        this.aiService.setCurrentConversation(conversation.conversation_id);
        this.shouldScroll = true;
        this.loading = false;
        this.changeDetectorRef.detectChanges();
      },
      (error) => {
        console.error('Error loading conversation:', error);

        // Check if we have cached messages
        const cachedMessages = this.aiService.getCachedMessages();
        if (cachedMessages && cachedMessages.length > 0) {
          this.messages = cachedMessages;
          this.usingCachedData = true;
          this.showCachedDataNotification();
        } else {
          this.startNewConversation();
        }

        this.loading = false;
      }
    );
  }

  showCachedDataNotification(): void {
    this.snackBar.open(
      'Using locally cached conversation data. Some messages may not be synchronized with the server.',
      'OK',
      { duration: 5000 }
    );
  }

  startNewConversation(): void {
    this.aiService.startNewConversation();
    this.conversationId = null;
    this.messages = [
      {
        role: 'system',
        content:
          'Hello! I am your AI Procurement Assistant. How can I help you today?',
        timestamp: new Date().toISOString(),
      },
    ];
    this.productSpecification = null;
    this.isSpecificationFinalized = false;
    this.shouldScroll = true;
    this.usingCachedData = false;
  }

  async sendMessage() {
    if (!this.newMessage.trim() || this.loading) return;

    const userMessage = this.newMessage.trim();
    this.newMessage = '';
    this.loading = true;
    this.shouldScroll = true;

    // Add user message to UI immediately for better UX
    this.messages.push({
      role: 'user',
      content: userMessage,
      timestamp: new Date().toISOString(),
    });

    try {
      const response = await this.aiService
        .generateResponse(userMessage)
        .toPromise();

      if (response) {
        // Update messages from server response
        this.messages = response.messages;
        this.conversationId = response.conversation_id;
        this.usingCachedData = false;

        // Store the conversation ID
        this.aiService.setCurrentConversation(response.conversation_id);

        // Check for product specification in the response
        if (response.productSpecification) {
          this.productSpecification = response.productSpecification;
          this.isSpecificationFinalized = response.isSpecificationFinalized;
        }
      }
    } catch (error) {
      console.error('Error getting AI response:', error);

      if (!this.usingCachedData) {
        this.messages.push({
          role: 'system',
          content: 'Sorry, I encountered an error. Please try again.',
          timestamp: new Date().toISOString(),
        });
      }

      this.usingCachedData = true;
    } finally {
      this.loading = false;
      this.changeDetectorRef.detectChanges();
    }
  }

  onKeyPress(event: KeyboardEvent) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      this.sendMessage();
    }
  }

  closeSpecification() {
    this.productSpecification = null;
    this.isSpecificationFinalized = false;
  }

  downloadSpecification() {
    if (!this.productSpecification) return;

    const specification = {
      ...this.productSpecification,
      timestamp: new Date().toISOString(),
    };

    const blob = new Blob([JSON.stringify(specification, null, 2)], {
      type: 'application/json',
    });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `product-specification-${new Date().toISOString()}.json`;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
  }
}
