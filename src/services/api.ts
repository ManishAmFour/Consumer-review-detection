import { supabase } from '../lib/supabase';

export interface UserProfile {
  id: string;
  user_id: string;
  full_name: string;
  phone?: string;
  date_of_birth?: string;
  location?: string;
  school?: string;
  current_class?: string;
  stream?: string;
  interests: string[];
  career_goals?: string;
}

export interface QuizResult {
  id: string;
  user_id: string;
  quiz_type: string;
  answers: Record<string, number>;
  results: any;
  completed_at: string;
}

export interface College {
  id: number;
  name: string;
  location: string;
  type: string;
  courses: string[];
  fees: string;
  rating: number;
  cutoff: string;
}

export interface TimelineEvent {
  id: string;
  user_id: string;
  title: string;
  description: string;
  event_date: string;
  category: string;
  status: string;
  reminder_set: boolean;
}

class ApiService {
  // User Profile Management
  async getUserProfile(): Promise<UserProfile | null> {
    const { data, error } = await supabase
      .from('user_profiles')
      .select('*')
      .single();

    if (error && error.code !== 'PGRST116') {
      throw error;
    }
    
    return data;
  }

  async updateUserProfile(profile: Partial<UserProfile>): Promise<UserProfile> {
    const { data, error } = await supabase
      .from('user_profiles')
      .upsert(profile)
      .select()
      .single();

    if (error) throw error;
    return data;
  }

  // Quiz Management
  async saveQuizResult(quizResult: Omit<QuizResult, 'id' | 'completed_at'>): Promise<QuizResult> {
    const { data: { user } } = await supabase.auth.getUser();
    if (!user) throw new Error('User not authenticated');

    const { data, error } = await supabase
      .from('quiz_results')
      .insert({
        ...quizResult,
        user_id: user.id
      })
      .select()
      .single();

    if (error) throw error;
    return data;
  }

  async getQuizResults(): Promise<QuizResult[]> {
    const { data, error } = await supabase
      .from('quiz_results')
      .select('*')
      .order('completed_at', { ascending: false });

    if (error) throw error;
    return data;
  }

  // College Management
  async saveCollege(collegeName: string, collegeId: string): Promise<void> {
    const { data: { user } } = await supabase.auth.getUser();
    if (!user) throw new Error('User not authenticated');

    const { error } = await supabase
      .from('user_colleges')
      .insert({
        user_id: user.id,
        college_name: collegeName,
        college_id: collegeId,
        status: 'saved'
      });

    if (error) throw error;
  }

  async getSavedColleges(): Promise<any[]> {
    const { data, error } = await supabase
      .from('user_colleges')
      .select('*')
      .order('created_at', { ascending: false });

    if (error) throw error;
    return data;
  }

  // Timeline Management
  async getTimelineEvents(): Promise<TimelineEvent[]> {
    const { data, error } = await supabase
      .from('timeline_events')
      .select('*')
      .order('event_date', { ascending: true });

    if (error) throw error;
    return data;
  }

  async addTimelineEvent(event: Omit<TimelineEvent, 'id' | 'user_id'>): Promise<TimelineEvent> {
    const { data: { user } } = await supabase.auth.getUser();
    if (!user) throw new Error('User not authenticated');

    const { data, error } = await supabase
      .from('timeline_events')
      .insert({
        ...event,
        user_id: user.id
      })
      .select()
      .single();

    if (error) throw error;
    return data;
  }

  // AI Recommendations
  async getAIRecommendations(userProfile: any) {
    try {
      const response = await fetch('/api/recommendations', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ userProfile }),
      });

      if (!response.ok) {
        throw new Error('Failed to get recommendations');
      }

      const data = await response.json();
      return data.recommendations;
    } catch (error) {
      console.error('Error getting AI recommendations:', error);
      throw error;
    }
  }

  // Mock College Data (would normally come from external API)
  async getColleges(filters?: { location?: string; type?: string; course?: string }): Promise<College[]> {
    // In a real implementation, this would call an external API or database
    return [
      {
        id: 1,
        name: 'Indian Institute of Technology Delhi',
        location: 'New Delhi, Delhi',
        type: 'Government',
        courses: ['Computer Science', 'Mechanical Engineering', 'Electrical Engineering'],
        fees: '₹2.5 LPA',
        rating: 4.8,
        cutoff: 'JEE Advanced Rank < 500'
      },
      {
        id: 2,
        name: 'Delhi Technological University',
        location: 'Delhi, Delhi',
        type: 'Government',
        courses: ['Information Technology', 'Electronics', 'Civil Engineering'],
        fees: '₹1.8 LPA',
        rating: 4.3,
        cutoff: 'JEE Main Rank < 15000'
      }
    ];
  }
}

export const apiService = new ApiService();