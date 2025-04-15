import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { DocumentCheck } from './document-check.entity';
import { DocumentCheckService } from './document-check.service';
import { DocumentCheckController } from './document-check.controller';

@Module({
  imports: [TypeOrmModule.forFeature([DocumentCheck])],
  providers: [DocumentCheckService],
  controllers: [DocumentCheckController],
})
export class DocumentCheckModule {} 