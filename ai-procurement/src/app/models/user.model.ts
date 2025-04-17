export interface User {
  email: string;
  phone: string;
  password?: string; // Only used during registration/login
}

export interface AuthResponse {
  user: User;
  token: string;
}
