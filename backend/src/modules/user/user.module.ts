import { Module, Logger } from '@nestjs/common';
import { UserController } from './user.controller';
import { UserService } from './user.service';

@Module({
  controllers: [UserController],
  providers: [UserService],
})
export class UserModule {
  private readonly logger = new Logger(UserModule.name);

  constructor() {
    this.logger.log('UserModule initialized');
  }
} 