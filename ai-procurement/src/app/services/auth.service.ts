import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';
import { User, AuthResponse } from '../models/user.model';
import { Router } from '@angular/router';

@Injectable({
  providedIn: 'root',
})
export class AuthService {
  private currentUserSubject = new BehaviorSubject<User | null>(null);
  public currentUser$ = this.currentUserSubject.asObservable();
  public get currentUser(): User | null {
    return this.currentUserSubject.value;
  }

  constructor(private router: Router) {
    // Check for stored user data
    const storedUser = localStorage.getItem('currentUser');
    if (storedUser) {
      this.currentUserSubject.next(JSON.parse(storedUser));
    }
  }

  register(user: User): Observable<AuthResponse> {
    // In a real application, this would make an HTTP request to your backend
    return new Observable<AuthResponse>((subscriber) => {
      // Simulate API call
      setTimeout(() => {
        const response: AuthResponse = {
          user: { email: user.email, phone: user.phone },
          token: 'dummy-token-' + Math.random(),
        };
        this.setCurrentUser(response.user);
        subscriber.next(response);
        subscriber.complete();
      }, 1000);
    });
  }

  login(email: string, password: string): Observable<AuthResponse> {
    // In a real application, this would make an HTTP request to your backend
    return new Observable<AuthResponse>((subscriber) => {
      // Simulate API call
      setTimeout(() => {
        const response: AuthResponse = {
          user: { email, phone: '+421900123456' }, // Dummy data
          token: 'dummy-token-' + Math.random(),
        };
        this.setCurrentUser(response.user);
        subscriber.next(response);
        subscriber.complete();
      }, 1000);
    });
  }

  logout(): void {
    localStorage.removeItem('currentUser');
    this.currentUserSubject.next(null);
    this.router.navigate(['/auth']);
  }

  private setCurrentUser(user: User): void {
    localStorage.setItem('currentUser', JSON.stringify(user));
    this.currentUserSubject.next(user);
  }

  isAuthenticated(): boolean {
    return this.currentUserSubject.value !== null;
  }
}
