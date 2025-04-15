import { Controller, Post, Get, Body, Param, Logger, Res } from '@nestjs/common';
import { AuthService } from './auth.service';
import { Response } from 'express';

@Controller('auth')
export class AuthController {
  private readonly logger = new Logger(AuthController.name);

  constructor(private readonly authService: AuthService) {}

  @Post('register')
  async register(@Body('email') email: string) {
    this.logger.log(`Registration request received for email: ${email}`);
    return this.authService.register(email);
  }

  @Get('verify-email/:token')
  async verifyEmail(@Param('token') token: string, @Res() res: Response) {
    try {
      const result = await this.authService.verifyEmail(token);
      // Redirect to success page or return success response
      return res.status(200).json(result);
    } catch (error) {
      this.logger.error('Email verification failed:', error);
      // Redirect to error page or return error response
      return res.status(400).json({ error: 'Email verification failed' });
    }
  }

  @Post('login')
  async login(@Body('email') email: string) {
    this.logger.log(`Login request received for email: ${email}`);
    return this.authService.login(email);
  }

  @Get('validate-login/:token')
  async validateLogin(@Param('token') token: string, @Res() res: Response) {
    try {
      const result = await this.authService.validateLoginToken(token);
      return res.status(200).json(result);
    } catch (error) {
      this.logger.error('Login validation failed:', error);
      return res.status(400).json({ error: 'Invalid or expired login link' });
    }
  }
} 