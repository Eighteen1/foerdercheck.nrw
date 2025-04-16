import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { DocumentCheckModule } from './modules/document-check/document-check.module';
import { DocumentCheck } from './modules/document-check/document-check.entity';
import { AuthModule } from './modules/auth/auth.module';
import { UserModule } from './modules/user/user.module';

@Module({
  imports: [
    TypeOrmModule.forRoot({
      type: 'sqlite',
      database: 'foerdercheck.db',
      entities: [DocumentCheck],
      synchronize: true, // Set to false in production
    }),
    AuthModule,
    DocumentCheckModule,
    UserModule,
  ],
})
export class AppModule {}
