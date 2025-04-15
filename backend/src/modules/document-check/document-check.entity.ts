import { Entity, Column, PrimaryGeneratedColumn, CreateDateColumn, UpdateDateColumn } from 'typeorm';

@Entity()
export class DocumentCheck {
  @PrimaryGeneratedColumn()
  id: number;

  @Column()
  userId: string;

  @Column('json')
  propertyType: string;

  @Column('json')
  answers: {
    hasInheritanceRight: boolean;
    hasLocationCostLoan: boolean;
    hasWoodConstructionLoan: boolean;
    hasBEGStandardLoan: boolean;
    isPregnant: boolean;
    isMarried: boolean;
    isDisabled: boolean;
    hasAuthorizedPerson: boolean;
  };

  @CreateDateColumn()
  createdAt: Date;

  @UpdateDateColumn()
  updatedAt: Date;
} 