import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import {
  FormsModule,
  ReactiveFormsModule,
  FormBuilder,
  FormGroup,
  Validators,
} from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { Router } from '@angular/router';
import { AuthService } from '../../services/auth.service';

@Component({
  selector: 'app-auth',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    MatCardModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatIconModule,
  ],
  templateUrl: './auth.component.html',
  styleUrl: './auth.component.scss',
})
export class AuthComponent {
  isLogin = true;
  authForm: FormGroup;
  error: string | null = null;

  constructor(
    private fb: FormBuilder,
    private authService: AuthService,
    private router: Router
  ) {
    this.authForm = this.fb.group({
      email: ['', [Validators.required, Validators.email]],
      password: ['', [Validators.required, Validators.minLength(6)]],
      phone: [
        '',
        [Validators.required, Validators.pattern(/^\+?[1-9]\d{1,14}$/)],
      ],
    });
  }

  toggleMode() {
    this.isLogin = !this.isLogin;
    this.error = null;
  }

  onSubmit() {
    if (this.authForm.valid) {
      const { email, password, phone } = this.authForm.value;
      if (this.isLogin) {
        this.authService.login(email, password).subscribe({
          next: () => this.router.navigate(['/chat']),
          error: (err) => (this.error = err.message),
        });
      } else {
        this.authService.register({ email, password, phone }).subscribe({
          next: () => {
            this.isLogin = true;
            this.error = null;
          },
          error: (err) => (this.error = err.message),
        });
      }
    }
  }
}
