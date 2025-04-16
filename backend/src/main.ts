import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module';
import { Logger } from '@nestjs/common';

async function bootstrap() {
  const logger = new Logger('Bootstrap');
  const app = await NestFactory.create(AppModule);
  
  // Temporarily remove global prefix
  // app.setGlobalPrefix('api');
  logger.log('Starting application without global prefix');
  
  app.enableCors({
    origin: ['http://localhost:3000', 'https://foerdercheck-nrw-frontend.vercel.app'],
    methods: 'GET,HEAD,PUT,PATCH,POST,DELETE',
    credentials: true,
  });
  
  const port = process.env.PORT ?? 8000;
  await app.listen(port);
  logger.log(`Application is running on: ${port}`);
}
bootstrap();
