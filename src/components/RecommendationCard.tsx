import React from 'react';
import { TrendingUp, ExternalLink } from 'lucide-react';

interface Recommendation {
  id: number;
  title: string;
  description: string;
  confidence: number;
  category: string;
}

interface RecommendationCardProps {
  recommendation: Recommendation;
}

export const RecommendationCard: React.FC<RecommendationCardProps> = ({ recommendation }) => {
  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 90) return 'text-green-600 bg-green-100';
    if (confidence >= 80) return 'text-yellow-600 bg-yellow-100';
    return 'text-orange-600 bg-orange-100';
  };

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6 hover:shadow-lg transition-all duration-200 group">
      <div className="flex items-start justify-between mb-4">
        <div className="flex-1">
          <h3 className="text-lg font-semibold text-gray-900 mb-1 group-hover:text-blue-600 transition-colors">
            {recommendation.title}
          </h3>
          <span className="inline-block px-3 py-1 bg-blue-100 text-blue-800 text-sm rounded-full">
            {recommendation.category}
          </span>
        </div>
        <ExternalLink className="h-5 w-5 text-gray-400 group-hover:text-blue-600 transition-colors" />
      </div>
      
      <p className="text-gray-600 mb-4">
        {recommendation.description}
      </p>
      
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <TrendingUp className="h-4 w-4 text-gray-400" />
          <span className="text-sm text-gray-500">Confidence</span>
        </div>
        <span className={`px-3 py-1 rounded-full text-sm font-medium ${getConfidenceColor(recommendation.confidence)}`}>
          {recommendation.confidence}%
        </span>
      </div>
    </div>
  );
};