import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { 
  BookOpen, 
  TrendingUp, 
  MapPin, 
  Clock, 
  Brain, 
  Target,
  Award,
  Users
} from 'lucide-react';
import { RecommendationCard } from '../components/RecommendationCard';
import { StatsCard } from '../components/StatsCard';

export const Dashboard: React.FC = () => {
  const { user } = useAuth();
  const [recommendations, setRecommendations] = useState([]);

  useEffect(() => {
    // Mock AI recommendations
    setRecommendations([
      {
        id: 1,
        title: 'Computer Science Engineering',
        description: 'Based on your strong performance in mathematics and interest in technology',
        confidence: 92,
        category: 'Engineering'
      },
      {
        id: 2,
        title: 'Data Science Program',
        description: 'Your analytical skills and problem-solving abilities align perfectly',
        confidence: 88,
        category: 'Technology'
      },
      {
        id: 3,
        title: 'Digital Marketing Course',
        description: 'Creative thinking combined with technical aptitude shows great potential',
        confidence: 85,
        category: 'Business'
      }
    ]);
  }, []);

  if (!user) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-3xl font-bold text-gray-900 mb-4">Welcome to EduGuide</h1>
          <p className="text-gray-600 mb-8">Your personalized career and education advisor</p>
          <Link
            to="/login"
            className="bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 transition-colors"
          >
            Get Started
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Welcome Section */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">
          Welcome back, {user.full_name || user.email}!
        </h1>
        <p className="text-gray-600">
          Your personalized education and career guidance dashboard
        </p>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        <StatsCard
          title="Quizzes Taken"
          value="3"
          icon={<Brain className="h-6 w-6 text-blue-600" />}
          trend="+2 this month"
        />
        <StatsCard
          title="Career Matches"
          value="12"
          icon={<Target className="h-6 w-6 text-green-600" />}
          trend="Updated today"
        />
        <StatsCard
          title="Saved Colleges"
          value="8"
          icon={<BookOpen className="h-6 w-6 text-purple-600" />}
          trend="3 new matches"
        />
        <StatsCard
          title="Deadlines"
          value="5"
          icon={<Clock className="h-6 w-6 text-orange-600" />}
          trend="2 upcoming"
        />
      </div>

      {/* AI Recommendations */}
      <div className="mb-8">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold text-gray-900">AI Recommendations</h2>
          <Link
            to="/quiz"
            className="text-blue-600 hover:text-blue-700 font-medium transition-colors"
          >
            Take Assessment →
          </Link>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {recommendations.map((rec: any) => (
            <RecommendationCard key={rec.id} recommendation={rec} />
          ))}
        </div>
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
        <Link
          to="/quiz"
          className="bg-gradient-to-br from-blue-500 to-blue-600 text-white p-6 rounded-xl hover:shadow-lg transition-all duration-200 group"
        >
          <div className="flex items-center space-x-3 mb-4">
            <Brain className="h-8 w-8 group-hover:scale-110 transition-transform" />
            <h3 className="text-xl font-semibold">Take Assessment</h3>
          </div>
          <p className="text-blue-100">
            Discover your strengths and interests with our comprehensive quiz
          </p>
        </Link>

        <Link
          to="/career-mapping"
          className="bg-gradient-to-br from-green-500 to-green-600 text-white p-6 rounded-xl hover:shadow-lg transition-all duration-200 group"
        >
          <div className="flex items-center space-x-3 mb-4">
            <TrendingUp className="h-8 w-8 group-hover:scale-110 transition-transform" />
            <h3 className="text-xl font-semibold">Career Paths</h3>
          </div>
          <p className="text-green-100">
            Explore detailed career mapping and opportunities
          </p>
        </Link>

        <Link
          to="/colleges"
          className="bg-gradient-to-br from-purple-500 to-purple-600 text-white p-6 rounded-xl hover:shadow-lg transition-all duration-200 group"
        >
          <div className="flex items-center space-x-3 mb-4">
            <MapPin className="h-8 w-8 group-hover:scale-110 transition-transform" />
            <h3 className="text-xl font-semibold">Find Colleges</h3>
          </div>
          <p className="text-purple-100">
            Discover nearby colleges with detailed information
          </p>
        </Link>
      </div>

      {/* Recent Activity */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <h3 className="text-xl font-bold text-gray-900 mb-4">Recent Activity</h3>
        <div className="space-y-4">
          <div className="flex items-center space-x-3 p-3 bg-gray-50 rounded-lg">
            <Award className="h-5 w-5 text-yellow-500" />
            <span className="text-gray-700">Completed Aptitude Assessment - Science Stream</span>
            <span className="text-sm text-gray-500 ml-auto">2 hours ago</span>
          </div>
          <div className="flex items-center space-x-3 p-3 bg-gray-50 rounded-lg">
            <Users className="h-5 w-5 text-blue-500" />
            <span className="text-gray-700">Saved IIT Delhi to college wishlist</span>
            <span className="text-sm text-gray-500 ml-auto">1 day ago</span>
          </div>
          <div className="flex items-center space-x-3 p-3 bg-gray-50 rounded-lg">
            <BookOpen className="h-5 w-5 text-green-500" />
            <span className="text-gray-700">Viewed Computer Science career path</span>
            <span className="text-sm text-gray-500 ml-auto">3 days ago</span>
          </div>
        </div>
      </div>
    </div>
  );
};