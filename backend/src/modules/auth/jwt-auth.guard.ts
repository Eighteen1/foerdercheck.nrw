import { Injectable, CanActivate, ExecutionContext, UnauthorizedException, Logger } from '@nestjs/common';
import { JwtService } from '@nestjs/jwt';
import { Observable } from 'rxjs';
import { Request } from 'express';

@Injectable()
export class JwtAuthGuard implements CanActivate {
  private readonly logger = new Logger(JwtAuthGuard.name);

  constructor(private readonly jwtService: JwtService) {}

  canActivate(
    context: ExecutionContext,
  ): boolean | Promise<boolean> | Observable<boolean> {
    const request = context.switchToHttp().getRequest<Request>();
    const token = this.extractTokenFromHeader(request);
    
    if (!token) {
      this.logger.warn('Authentication failed: No token provided');
      throw new UnauthorizedException('No token provided');
    }

    try {
      const payload = this.jwtService.verify(token);
      if (!payload.email) {
        throw new UnauthorizedException('Invalid token payload');
      }
      
      this.logger.debug(`Authentication successful for user: ${payload.email}`);
      request['user'] = { id: payload.email };
      return true;
    } catch (error) {
      this.logger.error('Token validation failed:', error);
      throw new UnauthorizedException('Invalid or expired token');
    }
  }

  private extractTokenFromHeader(request: Request): string | undefined {
    const [type, token] = request.headers.authorization?.split(' ') ?? [];
    if (!type || !token) {
      this.logger.debug('No authorization header found or invalid format');
      return undefined;
    }
    if (type !== 'Bearer') {
      this.logger.debug(`Invalid authorization type: ${type}`);
      return undefined;
    }
    return token;
  }
} 