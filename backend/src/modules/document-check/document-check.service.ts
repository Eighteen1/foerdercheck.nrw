import { Injectable, Logger } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { DocumentCheck } from './document-check.entity';

@Injectable()
export class DocumentCheckService {
  private readonly logger = new Logger(DocumentCheckService.name);

  constructor(
    @InjectRepository(DocumentCheck)
    private documentCheckRepository: Repository<DocumentCheck>,
  ) {}

  async saveDocumentCheck(userEmail: string, data: Partial<DocumentCheck>): Promise<DocumentCheck> {
    this.logger.debug(`Attempting to save document check for user: ${userEmail}`);
    
    try {
      let documentCheck = await this.documentCheckRepository.findOne({
        where: { userId: userEmail },
      });

      if (!documentCheck) {
        this.logger.debug(`Creating new document check for user: ${userEmail}`);
        documentCheck = this.documentCheckRepository.create({
          userId: userEmail,
          ...data,
        });
      } else {
        this.logger.debug(`Updating existing document check for user: ${userEmail}`);
        this.documentCheckRepository.merge(documentCheck, data);
      }

      const savedDocument = await this.documentCheckRepository.save(documentCheck);
      this.logger.debug(`Successfully saved document check for user: ${userEmail}`);
      return savedDocument;
    } catch (error) {
      this.logger.error(`Error saving document check for user ${userEmail}:`, error);
      throw error;
    }
  }

  async getDocumentCheck(userEmail: string): Promise<DocumentCheck | null> {
    this.logger.debug(`Attempting to retrieve document check for user: ${userEmail}`);
    
    try {
      const documentCheck = await this.documentCheckRepository.findOne({
        where: { userId: userEmail },
      });

      if (documentCheck) {
        this.logger.debug(`Found document check for user: ${userEmail}`);
      } else {
        this.logger.debug(`No document check found for user: ${userEmail}`);
      }

      return documentCheck;
    } catch (error) {
      this.logger.error(`Error retrieving document check for user ${userEmail}:`, error);
      throw error;
    }
  }
} 