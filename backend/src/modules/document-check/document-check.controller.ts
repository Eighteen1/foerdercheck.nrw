import { Controller, Get, Post, Body, UseGuards, Request, Logger } from '@nestjs/common';
import { DocumentCheckService } from './document-check.service';
import { JwtAuthGuard } from '../auth/jwt-auth.guard';

interface RequestWithUser extends Request {
  user: {
    id: string; // This will be the user's email
  };
}

@Controller('document-check')
@UseGuards(JwtAuthGuard)
export class DocumentCheckController {
  private readonly logger = new Logger(DocumentCheckController.name);

  constructor(private readonly documentCheckService: DocumentCheckService) {}

  @Post('save')
  async saveDocumentCheck(
    @Request() req: RequestWithUser,
    @Body() documentCheckData: any
  ) {
    const userEmail = req.user.id;
    this.logger.log(`Received save request for user: ${userEmail}`);
    this.logger.debug('Document check data:', documentCheckData);

    try {
      const result = await this.documentCheckService.saveDocumentCheck(userEmail, {
        propertyType: documentCheckData.propertyType,
        answers: documentCheckData.answers,
      });
      this.logger.log(`Successfully saved document check for user: ${userEmail}`);
      return result;
    } catch (error) {
      this.logger.error(`Error saving document check for user ${userEmail}:`, error);
      throw error;
    }
  }

  @Get('load')
  async getDocumentCheck(@Request() req: RequestWithUser) {
    const userEmail = req.user.id;
    this.logger.log(`Received load request for user: ${userEmail}`);

    try {
      const result = await this.documentCheckService.getDocumentCheck(userEmail);
      if (result) {
        this.logger.log(`Successfully loaded document check for user: ${userEmail}`);
      } else {
        this.logger.log(`No document check found for user: ${userEmail}`);
      }
      return result;
    } catch (error) {
      this.logger.error(`Error loading document check for user ${userEmail}:`, error);
      throw error;
    }
  }
} 