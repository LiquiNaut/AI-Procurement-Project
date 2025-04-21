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
  ShoppingOption,
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
  shoppingOptions: ShoppingOption[] = [];
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
        console.log('Initializing component with cached messages');
        this.messages = cachedMessages;
        this.usingCachedData = true;
        this.showCachedDataNotification();
        // Try to find latest product spec and options in cache (if any)
        this.findLatestSpecAndOptionsInMessages(cachedMessages);
      } else {
        // Initialize with a welcome message for new conversations
        console.log('Initializing new conversation with welcome message');
        this.initializeWelcomeMessage();
      }
    }
  }

  private initializeWelcomeMessage() {
    this.messages = [
      {
        role: 'system',
        content:
          'Hello! I am your AI Procurement Assistant. How can I help you today?',
        timestamp: new Date().toISOString(),
      },
    ];
  }

  ngAfterViewChecked() {
    if (this.shouldScroll) {
      this.scrollToBottom();
      this.shouldScroll = false;
    }
  }

  private scrollToBottom(): void {
    // Only scroll if the container exists
    if (this.chatContainer && this.chatContainer.nativeElement) {
      try {
        const element = this.chatContainer.nativeElement;
        element.scrollTop = element.scrollHeight;
      } catch (err) {
        console.error('Error scrolling to bottom:', err);
      }
    }
  }

  loadConversation(conversationId: string): void {
    console.log(`Loading conversation: ${conversationId}`);
    this.loading = true;
    this.aiService.getConversation(conversationId).subscribe({
      next: (conversation) => {
        console.log(`Conversation ${conversationId} loaded successfully.`);
        this.messages = conversation.messages;
        this.conversationId = conversation.conversation_id;
        this.aiService.setCurrentConversation(conversation.conversation_id);
        // Find latest spec and options in the loaded messages
        this.findLatestSpecAndOptionsInMessages(this.messages);
        this.shouldScroll = true;
        this.loading = false;
        this.changeDetectorRef.detectChanges(); // Ensure view updates
      },
      error: (error) => {
        console.error('Error loading conversation:', error);
        // Attempt to use cache as fallback
        const cachedMessages = this.aiService.getCachedMessages();
        if (cachedMessages && cachedMessages.length > 0) {
          console.warn('Falling back to cached messages after load error.');
          this.messages = cachedMessages;
          this.usingCachedData = true;
          this.showCachedDataNotification();
          this.findLatestSpecAndOptionsInMessages(cachedMessages);
        } else {
          // If no cache, start fresh
          console.warn(
            'No cached messages available, starting new conversation after load error.'
          );
          this.startNewConversation();
        }
        this.loading = false;
        this.changeDetectorRef.detectChanges(); // Ensure view updates
      },
    });
  }

  showCachedDataNotification(): void {
    this.snackBar.open(
      'Using locally cached conversation data. Connection might be unstable.',
      'OK',
      { duration: 5000 }
    );
  }

  startNewConversation(): void {
    console.log('Starting new conversation');
    this.aiService.startNewConversation();
    this.conversationId = null;
    this.initializeWelcomeMessage();
    this.productSpecification = null;
    this.isSpecificationFinalized = false;
    this.shoppingOptions = []; // Clear options
    this.shouldScroll = true;
    this.usingCachedData = false;
    this.changeDetectorRef.detectChanges();
  }

  async sendMessage() {
    if (!this.newMessage.trim() || this.loading) return;

    const userMessage = this.newMessage.trim();
    console.log(`Sending message: ${userMessage}`);
    this.newMessage = '';
    this.loading = true;
    this.shouldScroll = true;

    // Add user message to UI immediately
    this.messages.push({
      role: 'user',
      content: userMessage,
      timestamp: new Date().toISOString(),
    });
    // Clear previous shopping options immediately for better UX
    this.shoppingOptions = [];
    this.changeDetectorRef.detectChanges();
    this.scrollToBottom(); // Scroll after adding user message

    try {
      const response = await this.aiService
        .generateResponse(userMessage)
        .toPromise();

      if (response) {
        console.log('Received response from AI service:', response);
        // Update messages from server response (most reliable source)
        this.messages = response.messages;
        this.conversationId = response.conversation_id;
        this.usingCachedData = false; // Assume connection restored if we got a response

        // Store the conversation ID
        this.aiService.setCurrentConversation(response.conversation_id);

        // Update product specification and shopping options from the response
        this.productSpecification = response.productSpecification || null;
        this.isSpecificationFinalized = response.isSpecificationFinalized;
        this.shoppingOptions = response.shoppingOptions || []; // Update shopping options

        if (this.shoppingOptions.length > 0) {
          console.log(
            `Received ${this.shoppingOptions.length} shopping options.`
          );
        }
      } else {
        console.error('Received null or undefined response from AI service');
        // Handle potential null response, maybe add error message
        this.addErrorMessageToChat(
          'Received an empty response from the server.'
        );
      }
    } catch (error) {
      console.error('Error getting AI response:', error);
      // The service now handles pushing an error message into cachedMessages on error
      this.messages = this.aiService.getCachedMessages(); // Reflect the cache state
      this.usingCachedData = true;
      this.showCachedDataNotification();
    } finally {
      this.loading = false;
      this.shouldScroll = true; // Ensure scroll after response/error
      this.changeDetectorRef.detectChanges(); // Trigger UI update
    }
  }

  // Helper to find the latest spec/options when loading history
  findLatestSpecAndOptionsInMessages(messages: Message[]) {
    // This is tricky as specs/options aren't stored directly in messages.
    // For now, we primarily rely on the latest response from sendMessage.
    // If needed later, the server could potentially add spec/options metadata
    // to the last assistant message in the history.
    console.log(
      'findLatestSpecAndOptionsInMessages is currently a placeholder.'
    );
    // Resetting state when loading history for simplicity for now
    this.productSpecification = null;
    this.isSpecificationFinalized = false;
    this.shoppingOptions = [];
  }

  addErrorMessageToChat(errorMessage: string) {
    this.messages.push({
      role: 'system',
      content: errorMessage,
      timestamp: new Date().toISOString(),
    });
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
    // Decide if closing the spec should also clear shopping options
    // this.shoppingOptions = [];
    this.changeDetectorRef.detectChanges();
  }

  downloadSpecification() {
    if (!this.productSpecification) return;
    console.log('Downloading specification...');

    const specification = {
      ...this.productSpecification,
      timestamp: new Date().toISOString(),
    };

    try {
      const blob = new Blob([JSON.stringify(specification, null, 2)], {
        type: 'application/json',
      });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      // Sanitize filename a bit
      const safeName = (this.productSpecification.name || 'product')
        .replace(/[^a-z0-9]/gi, '_')
        .toLowerCase();
      a.download = `spec-${safeName}-${Date.now()}.json`;
      document.body.appendChild(a);
      a.click();
      // Cleanup
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (e) {
      console.error('Error creating or downloading blob:', e);
      this.snackBar.open(
        'Error preparing specification for download.',
        'Close',
        { duration: 3000 }
      );
    }
  }
}
