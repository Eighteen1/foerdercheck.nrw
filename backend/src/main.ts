import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module';
import { Logger } from '@nestjs/common';

async function bootstrap() {
  const logger = new Logger('Bootstrap');
  const app = await NestFactory.create(AppModule);
  
  // Set global prefix and log it
  app.setGlobalPrefix('api');
  logger.log('Global prefix set to: api');
  
  app.enableCors({
    origin: ['http://localhost:3000', 'https://foerdercheck-nrw-frontend.vercel.app'], // Add your Vercel frontend URL
    methods: 'GET,HEAD,PUT,PATCH,POST,DELETE',
    credentials: true,
  });
  
  const port = process.env.PORT ?? 8000;
  await app.listen(port);
  logger.log(`Application is running on: ${port}`);
}
bootstrap();
