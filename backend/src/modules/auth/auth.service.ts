import { Injectable, Logger } from '@nestjs/common';
import { JwtService } from '@nestjs/jwt';

@Injectable()
export class AuthService {
  private readonly logger = new Logger(AuthService.name);
  private readonly verifiedEmails = new Set<string>(); // In production, use a database

  constructor(private readonly jwtService: JwtService) {}

  async register(email: string) {
    this.logger.log(`Registration request received for email: ${email}`);
    
    // Generate a verification token
    const verificationToken = this.jwtService.sign({ 
      email,
      type: 'verification',
      expiresIn: '24h' 
    });
    
    // In a real app, you would send an email here
    this.logger.debug(`Generated verification token for ${email}: ${verificationToken}`);
    
    return { 
      message: 'Verification email sent',
      token: verificationToken // For testing purposes, return the token
    };
  }

  async verifyEmail(token: string) {
    this.logger.log(`Verifying email with token: ${token}`);
    
    try {
      const payload = this.jwtService.verify(token);
      
      if (payload.type !== 'verification') {
        throw new Error('Invalid token type');
      }
      
      const email = payload.email;
      if (!email) {
        throw new Error('Invalid token payload');
      }
      
      // Mark email as verified
      this.verifiedEmails.add(email);
      this.logger.log(`Email verified: ${email}`);
      
      return { 
        success: true, 
        email
      };
    } catch (error) {
      this.logger.error('Email verification failed:', error);
      throw new Error('Invalid or expired verification link');
    }
  }

  async login(email: string) {
    this.logger.log(`Login request received for email: ${email}`);
    
    // Check if email is verified
    if (!this.verifiedEmails.has(email)) {
      throw new Error('Email not verified. Please verify your email first.');
    }
    
    // Generate a login token
    const loginToken = this.jwtService.sign({ 
      email,
      type: 'login',
      expiresIn: '1h'
    });
    
    // In a real app, you would send an email here
    this.logger.debug(`Generated login token for ${email}: ${loginToken}`);
    
    return { 
      message: 'Login link sent',
      token: loginToken // For testing purposes, return the token
    };
  }

  async validateLoginToken(token: string) {
    this.logger.log(`Validating login token`);
    
    try {
      const payload = this.jwtService.verify(token);
      
      if (payload.type !== 'login') {
        throw new Error('Invalid token type');
      }
      
      const email = payload.email;
      if (!email) {
        throw new Error('Invalid token payload');
      }
      
      // Generate a session token
      const sessionToken = this.jwtService.sign({ 
        email,
        type: 'session',
        expiresIn: '24h'
      });
      
      this.logger.log(`Login successful for: ${email}`);
      return { 
        success: true, 
        email,
        token: sessionToken
      };
    } catch (error) {
      this.logger.error('Login token validation failed:', error);
      throw new Error('Invalid or expired login link');
    }
  }
} 