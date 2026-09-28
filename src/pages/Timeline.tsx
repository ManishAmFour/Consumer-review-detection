import React, { useState } from 'react';
import { 
  Calendar, 
  Clock, 
  Bell, 
  CheckCircle, 
  AlertCircle,
  Plus,
  Filter
} from 'lucide-react';

interface TimelineEvent {
  id: number;
  title: string;
  description: string;
  date: string;
  time: string;
  category: 'exam' | 'admission' | 'scholarship' | 'deadline';
  status: 'upcoming' | 'completed' | 'urgent';
  daysLeft: number;
}

export const Timeline: React.FC = () => {
  const [events, setEvents] = useState<TimelineEvent[]>([
    {
      id: 1,
      title: 'JEE Main Registration',
      description: 'Last date to register for JEE Main 2024',
      date: '2024-01-30',
      time: '23:59',
      category: 'exam',
      status: 'urgent',
      daysLeft: 15
    },
    {
      id: 2,
      title: 'NEET Application',
      description: 'NEET UG 2024 application form submission',
      date: '2024-02-15',
      time: '23:59',
      category: 'exam',
      status: 'upcoming',
      daysLeft: 31
    },
    {
      id: 3,
      title: 'Merit Scholarship',
      description: 'State merit scholarship application deadline',
      date: '2024-02-20',
      time: '17:00',
      category: 'scholarship',
      status: 'upcoming',
      daysLeft: 36
    },
    {
      id: 4,
      title: 'College Admission',
      description: 'Delhi University admission process begins',
      date: '2024-03-01',
      time: '10:00',
      category: 'admission',
      status: 'upcoming',
      daysLeft: 45
    },
    {
      id: 5,
      title: 'Board Exam Results',
      description: 'CBSE 12th board exam results expected',
      date: '2024-01-10',
      time: '14:00',
      category: 'exam',
      status: 'completed',
      daysLeft: -5
    }
  ]);

  const [filterCategory, setFilterCategory] = useState('all');

  const filteredEvents = events.filter(event => 
    filterCategory === 'all' || event.category === filterCategory
  );

  const getCategoryColor = (category: string) => {
    switch (category) {
      case 'exam': return 'bg-blue-100 text-blue-800';
      case 'admission': return 'bg-green-100 text-green-800';
      case 'scholarship': return 'bg-purple-100 text-purple-800';
      case 'deadline': return 'bg-orange-100 text-orange-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed': return <CheckCircle className="h-5 w-5 text-green-600" />;
      case 'urgent': return <AlertCircle className="h-5 w-5 text-red-600" />;
      default: return <Clock className="h-5 w-5 text-blue-600" />;
    }
  };

  const upcomingEvents = filteredEvents.filter(e => e.status !== 'completed').length;
  const urgentEvents = filteredEvents.filter(e => e.status === 'urgent').length;

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <div className="text-center mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Timeline Tracker</h1>
        <p className="text-gray-600">Stay on top of important deadlines and events</p>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="bg-blue-50 border border-blue-200 rounded-xl p-6 text-center">
          <Calendar className="h-8 w-8 text-blue-600 mx-auto mb-2" />
          <h3 className="text-2xl font-bold text-blue-900">{upcomingEvents}</h3>
          <p className="text-blue-700">Upcoming Events</p>
        </div>
        <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-center">
          <AlertCircle className="h-8 w-8 text-red-600 mx-auto mb-2" />
          <h3 className="text-2xl font-bold text-red-900">{urgentEvents}</h3>
          <p className="text-red-700">Urgent Deadlines</p>
        </div>
        <div className="bg-green-50 border border-green-200 rounded-xl p-6 text-center">
          <Bell className="h-8 w-8 text-green-600 mx-auto mb-2" />
          <h3 className="text-2xl font-bold text-green-900">3</h3>
          <p className="text-green-700">Active Reminders</p>
        </div>
      </div>

      {/* Controls */}
      <div className="bg-white rounded-xl shadow-lg p-6 mb-8">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between space-y-4 sm:space-y-0">
          <div className="flex items-center space-x-4">
            <Filter className="h-5 w-5 text-gray-500" />
            <select
              value={filterCategory}
              onChange={(e) => setFilterCategory(e.target.value)}
              className="border border-gray-300 rounded-lg px-4 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="all">All Categories</option>
              <option value="exam">Exams</option>
              <option value="admission">Admissions</option>
              <option value="scholarship">Scholarships</option>
              <option value="deadline">Deadlines</option>
            </select>
          </div>
          <button className="flex items-center space-x-2 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors">
            <Plus className="h-4 w-4" />
            <span>Add Event</span>
          </button>
        </div>
      </div>

      {/* Timeline */}
      <div className="space-y-4">
        {filteredEvents.map((event, index) => (
          <div key={event.id} className="relative">
            {index !== filteredEvents.length - 1 && (
              <div className="absolute left-8 top-16 w-0.5 h-full bg-gray-200"></div>
            )}
            
            <div className={`bg-white rounded-xl shadow-lg border-l-4 p-6 ml-4 transition-all hover:shadow-xl ${
              event.status === 'urgent' ? 'border-l-red-500' :
              event.status === 'completed' ? 'border-l-green-500' :
              'border-l-blue-500'
            }`}>
              <div className="flex items-start space-x-4">
                <div className={`p-2 rounded-full ${
                  event.status === 'urgent' ? 'bg-red-100' :
                  event.status === 'completed' ? 'bg-green-100' :
                  'bg-blue-100'
                }`}>
                  {getStatusIcon(event.status)}
                </div>
                
                <div className="flex-1">
                  <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-3">
                    <h3 className="text-lg font-semibold text-gray-900">{event.title}</h3>
                    <div className="flex items-center space-x-4">
                      <span className={`px-3 py-1 rounded-full text-sm font-medium ${getCategoryColor(event.category)}`}>
                        {event.category}
                      </span>
                      {event.status !== 'completed' && (
                        <span className={`text-sm font-medium ${
                          event.daysLeft <= 7 ? 'text-red-600' : 'text-gray-600'
                        }`}>
                          {event.daysLeft > 0 ? `${event.daysLeft} days left` : 'Overdue'}
                        </span>
                      )}
                    </div>
                  </div>
                  
                  <p className="text-gray-600 mb-3">{event.description}</p>
                  
                  <div className="flex items-center space-x-6 text-sm text-gray-500">
                    <div className="flex items-center">
                      <Calendar className="h-4 w-4 mr-1" />
                      {new Date(event.date).toLocaleDateString('en-IN', {
                        year: 'numeric',
                        month: 'long',
                        day: 'numeric'
                      })}
                    </div>
                    <div className="flex items-center">
                      <Clock className="h-4 w-4 mr-1" />
                      {event.time}
                    </div>
                  </div>
                </div>
              </div>
              
              {event.status !== 'completed' && (
                <div className="mt-4 flex space-x-3">
                  <button className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors text-sm">
                    Set Reminder
                  </button>
                  <button className="border border-gray-300 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-50 transition-colors text-sm">
                    More Info
                  </button>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};