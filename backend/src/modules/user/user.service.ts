import { Injectable, Logger } from '@nestjs/common';
import { createClient } from '@supabase/supabase-js';

@Injectable()
export class UserService {
  private readonly logger = new Logger(UserService.name);
  private supabaseAdmin;

  constructor() {
    if (!process.env.SUPABASE_URL || !process.env.SUPABASE_SERVICE_KEY) {
      throw new Error('Missing required Supabase environment variables');
    }
    this.supabaseAdmin = createClient(
      process.env.SUPABASE_URL,
      process.env.SUPABASE_SERVICE_KEY,
      {
        auth: {
          autoRefreshToken: false,
          persistSession: false
        }
      }
    );
  }

  async createUser(email: string) {
    try {
      // Create user in Supabase Auth
      const { data: authData, error: authError } = await this.supabaseAdmin.auth.admin.createUser({
        email,
        email_confirm: true,
        user_metadata: {
          created_via: 'foerdercheck'
        }
      });

      if (authError) {
        this.logger.error('Error creating user:', authError);
        throw authError;
      }

      // Create initial user_data record
      const { data: userData, error: userError } = await this.supabaseAdmin
        .from('user_data')
        .insert([
          {
            id: authData.user.id,
            eligibility_data: null,
            application_status: 'pending',
            document_status: {}
          }
        ]);

      if (userError) {
        this.logger.error('Error creating user_data record:', userError);
        throw userError;
      }

      return { user: authData.user };
    } catch (error) {
      this.logger.error('Error in createUser:', error);
      throw error;
    }
  }

  async storeEligibilityData(userId: string, eligibilityData: any) {
    try {
      const { data, error } = await this.supabaseAdmin
        .from('user_data')
        .update({
          eligibility_data: eligibilityData,
          updated_at: new Date().toISOString()
        })
        .eq('id', userId);

      if (error) {
        this.logger.error('Error storing eligibility data:', error);
        throw error;
      }

      return data;
    } catch (error) {
      this.logger.error('Error in storeEligibilityData:', error);
      throw error;
    }
  }
} 