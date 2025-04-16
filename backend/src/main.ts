import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module';
import { Logger } from '@nestjs/common';

async function bootstrap() {
  const logger = new Logger('Bootstrap');
  try {
    logger.log('Starting application bootstrap...');
    const app = await NestFactory.create(AppModule, { logger: ['error', 'warn', 'log', 'debug', 'verbose'] });
    logger.log('NestFactory created successfully');
    
    // Temporarily remove global prefix
    // app.setGlobalPrefix('api');
    logger.log('Starting application without global prefix');
    
    app.enableCors({
      origin: ['http://localhost:3000', 'https://foerdercheck-nrw-frontend.vercel.app'],
      methods: 'GET,HEAD,PUT,PATCH,POST,DELETE',
      credentials: true,
    });
    logger.log('CORS enabled');
    
    const port = process.env.PORT ?? 8000;
    await app.listen(port);
    logger.log(`Application is running on: ${port}`);
  } catch (error) {
    logger.error('Error during bootstrap:', error);
    throw error;
  }
}
bootstrap();
