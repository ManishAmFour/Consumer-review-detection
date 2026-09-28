import React, { useState } from 'react';
import { 
  BookOpen, 
  Download, 
  ExternalLink, 
  Star,
  Filter,
  Search,
  FileText,
  Video,
  Globe
} from 'lucide-react';

interface Resource {
  id: number;
  title: string;
  description: string;
  type: 'ebook' | 'video' | 'course' | 'scholarship' | 'tool';
  category: string;
  rating: number;
  downloads: number;
  url: string;
  thumbnail: string;
  author: string;
  duration?: string;
  level: 'Beginner' | 'Intermediate' | 'Advanced';
}

export const Resources: React.FC = () => {
  const [resources, setResources] = useState<Resource[]>([
    {
      id: 1,
      title: 'Complete Guide to JEE Main Preparation',
      description: 'Comprehensive study material covering all subjects for JEE Main examination',
      type: 'ebook',
      category: 'Engineering',
      rating: 4.8,
      downloads: 15420,
      url: '#',
      thumbnail: 'https://images.pexels.com/photos/159711/books-bookstore-book-reading-159711.jpeg',
      author: 'Dr. Amit Kumar',
      level: 'Intermediate'
    },
    {
      id: 2,
      title: 'Data Science Fundamentals',
      description: 'Learn the basics of data science, statistics, and machine learning',
      type: 'course',
      category: 'Technology',
      rating: 4.9,
      downloads: 8750,
      url: '#',
      thumbnail: 'https://images.pexels.com/photos/270348/pexels-photo-270348.jpeg',
      author: 'Tech Academy',
      duration: '12 hours',
      level: 'Beginner'
    },
    {
      id: 3,
      title: 'National Merit Scholarship Guide',
      description: 'Complete information about scholarship opportunities and application process',
      type: 'scholarship',
      category: 'Financial Aid',
      rating: 4.7,
      downloads: 12300,
      url: '#',
      thumbnail: 'https://images.pexels.com/photos/267885/pexels-photo-267885.jpeg',
      author: 'EduGuide Team',
      level: 'Beginner'
    },
    {
      id: 4,
      title: 'Career Planning Workshop',
      description: 'Interactive video series on career planning and goal setting',
      type: 'video',
      category: 'Career Development',
      rating: 4.6,
      downloads: 9200,
      url: '#',
      thumbnail: 'https://images.pexels.com/photos/3184465/pexels-photo-3184465.jpeg',
      author: 'Career Experts',
      duration: '2.5 hours',
      level: 'Beginner'
    },
    {
      id: 5,
      title: 'Resume Builder Tool',
      description: 'Professional resume builder with templates for students and freshers',
      type: 'tool',
      category: 'Career Development',
      rating: 4.5,
      downloads: 18500,
      url: '#',
      thumbnail: 'https://images.pexels.com/photos/590016/pexels-photo-590016.jpeg',
      author: 'EduGuide Team',
      level: 'Beginner'
    },
    {
      id: 6,
      title: 'Advanced Mathematics for Engineering',
      description: 'In-depth coverage of calculus, linear algebra, and differential equations',
      type: 'ebook',
      category: 'Engineering',
      rating: 4.9,
      downloads: 7650,
      url: '#',
      thumbnail: 'https://images.pexels.com/photos/3729557/pexels-photo-3729557.jpeg',
      author: 'Prof. Mathematics',
      level: 'Advanced'
    }
  ]);

  const [searchTerm, setSearchTerm] = useState('');
  const [filterType, setFilterType] = useState('all');
  const [filterCategory, setFilterCategory] = useState('all');

  const filteredResources = resources.filter(resource => {
    const matchesSearch = resource.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         resource.description.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesType = filterType === 'all' || resource.type === filterType;
    const matchesCategory = filterCategory === 'all' || resource.category === filterCategory;
    return matchesSearch && matchesType && matchesCategory;
  });

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'ebook': return <FileText className="h-5 w-5" />;
      case 'video': return <Video className="h-5 w-5" />;
      case 'course': return <BookOpen className="h-5 w-5" />;
      case 'tool': return <Globe className="h-5 w-5" />;
      default: return <FileText className="h-5 w-5" />;
    }
  };

  const getTypeColor = (type: string) => {
    switch (type) {
      case 'ebook': return 'bg-blue-100 text-blue-800';
      case 'video': return 'bg-red-100 text-red-800';
      case 'course': return 'bg-green-100 text-green-800';
      case 'scholarship': return 'bg-purple-100 text-purple-800';
      case 'tool': return 'bg-orange-100 text-orange-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const categories = [...new Set(resources.map(r => r.category))];

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <div className="text-center mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Resource Hub</h1>
        <p className="text-gray-600">Curated educational materials and tools for your success</p>
      </div>

      {/* Search and Filters */}
      <div className="bg-white rounded-xl shadow-lg p-6 mb-8">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-5 w-5" />
            <input
              type="text"
              placeholder="Search resources..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
          
          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
            className="px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          >
            <option value="all">All Types</option>
            <option value="ebook">E-books</option>
            <option value="video">Videos</option>
            <option value="course">Courses</option>
            <option value="scholarship">Scholarships</option>
            <option value="tool">Tools</option>
          </select>

          <select
            value={filterCategory}
            onChange={(e) => setFilterCategory(e.target.value)}
            className="px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          >
            <option value="all">All Categories</option>
            {categories.map(category => (
              <option key={category} value={category}>{category}</option>
            ))}
          </select>

          <button className="bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 transition-colors">
            <Filter className="h-4 w-4 inline mr-2" />
            Apply Filters
          </button>
        </div>
      </div>

      {/* Resource Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {filteredResources.map((resource) => (
          <div key={resource.id} className="bg-white rounded-xl shadow-lg border border-gray-200 overflow-hidden hover:shadow-xl transition-all duration-200 group">
            <div className="aspect-video bg-gray-100 relative overflow-hidden">
              <img 
                src={resource.thumbnail} 
                alt={resource.title}
                className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-200"
              />
              <div className="absolute top-4 left-4">
                <span className={`px-3 py-1 rounded-full text-sm font-medium ${getTypeColor(resource.type)}`}>
                  {resource.type}
                </span>
              </div>
              <div className="absolute top-4 right-4">
                <span className="px-2 py-1 bg-black bg-opacity-70 text-white text-xs rounded">
                  {resource.level}
                </span>
              </div>
            </div>
            
            <div className="p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-2 group-hover:text-blue-600 transition-colors">
                {resource.title}
              </h3>
              <p className="text-gray-600 text-sm mb-4 line-clamp-2">
                {resource.description}
              </p>
              
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center space-x-1">
                  <Star className="h-4 w-4 text-yellow-500" />
                  <span className="text-sm font-medium text-gray-700">{resource.rating}</span>
                  <span className="text-sm text-gray-500">({resource.downloads.toLocaleString()} downloads)</span>
                </div>
              </div>
              
              <div className="flex items-center justify-between mb-4">
                <span className="text-sm text-gray-500">by {resource.author}</span>
                {resource.duration && (
                  <span className="text-sm text-gray-500">{resource.duration}</span>
                )}
              </div>
              
              <div className="flex space-x-3">
                <button className="flex-1 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors flex items-center justify-center space-x-2">
                  <Download className="h-4 w-4" />
                  <span>Access</span>
                </button>
                <button className="p-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors">
                  <ExternalLink className="h-4 w-4 text-gray-600" />
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>

      {filteredResources.length === 0 && (
        <div className="text-center py-12">
          <BookOpen className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No resources found</h3>
          <p className="text-gray-500">Try adjusting your search criteria</p>
        </div>
      )}
    </div>
  );
};