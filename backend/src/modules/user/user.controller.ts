import { Controller, Post, Body, Logger } from '@nestjs/common';
import { UserService } from './user.service';

@Controller('user')
export class UserController {
  private readonly logger = new Logger(UserController.name);

  constructor(private readonly userService: UserService) {}

  @Post('create')
  async createUser(@Body('email') email: string) {
    this.logger.log(`Received create user request for email: ${email}`);
    try {
      const result = await this.userService.createUser(email);
      this.logger.log(`Successfully created user: ${JSON.stringify(result)}`);
      return result;
    } catch (error) {
      this.logger.error(`Error creating user: ${error.message}`, error.stack);
      throw error;
    }
  }

  @Post('store-eligibility')
  async storeEligibilityData(
    @Body('userId') userId: string,
    @Body('eligibilityData') eligibilityData: any
  ) {
    this.logger.log(`Storing eligibility data for user: ${userId}`);
    return this.userService.storeEligibilityData(userId, eligibilityData);
  }
} 