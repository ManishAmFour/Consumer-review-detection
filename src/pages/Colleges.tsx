import React, { useState, useEffect } from 'react';
import { 
  MapPin, 
  Star, 
  Phone, 
  Globe, 
  Users, 
  BookOpen,
  Filter,
  Search
} from 'lucide-react';

interface College {
  id: number;
  name: string;
  location: string;
  type: 'Government' | 'Private' | 'Autonomous';
  rating: number;
  fees: string;
  courses: string[];
  cutoff: string;
  facilities: string[];
  distance: string;
  contact: {
    phone: string;
    website: string;
  };
}

export const Colleges: React.FC = () => {
  const [colleges, setColleges] = useState<College[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterType, setFilterType] = useState('All');
  const [selectedCollege, setSelectedCollege] = useState<College | null>(null);

  useEffect(() => {
    // Mock college data
    setColleges([
      {
        id: 1,
        name: 'Indian Institute of Technology Delhi',
        location: 'New Delhi, Delhi',
        type: 'Government',
        rating: 4.8,
        fees: '₹2.5 LPA',
        courses: ['Computer Science', 'Mechanical Engineering', 'Electrical Engineering'],
        cutoff: 'JEE Advanced Rank < 500',
        facilities: ['Hostel', 'Library', 'Labs', 'Sports Complex', 'WiFi'],
        distance: '12 km from your location',
        contact: {
          phone: '+91-11-2659-1020',
          website: 'www.iitd.ac.in'
        }
      },
      {
        id: 2,
        name: 'Delhi Technological University',
        location: 'Delhi, Delhi',
        type: 'Government',
        rating: 4.3,
        fees: '₹1.8 LPA',
        courses: ['Information Technology', 'Electronics', 'Civil Engineering'],
        cutoff: 'JEE Main Rank < 15000',
        facilities: ['Hostel', 'Library', 'Cafeteria', 'WiFi', 'Placement Cell'],
        distance: '8 km from your location',
        contact: {
          phone: '+91-11-2787-2983',
          website: 'www.dtu.ac.in'
        }
      },
      {
        id: 3,
        name: 'NMIMS Mumbai',
        location: 'Mumbai, Maharashtra',
        type: 'Private',
        rating: 4.2,
        fees: '₹4.5 LPA',
        courses: ['Business Administration', 'Commerce', 'Economics'],
        cutoff: 'NPAT Score > 150',
        facilities: ['Modern Campus', 'Industry Partnerships', 'International Programs'],
        distance: '1200 km from your location',
        contact: {
          phone: '+91-22-4235-4200',
          website: 'www.nmims.edu'
        }
      }
    ]);
  }, []);

  const filteredColleges = colleges.filter(college => {
    const matchesSearch = college.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         college.location.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesType = filterType === 'All' || college.type === filterType;
    return matchesSearch && matchesType;
  });

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <div className="text-center mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">College Directory</h1>
        <p className="text-gray-600">Find and explore colleges near you with detailed information</p>
      </div>

      {/* Search & Filter */}
      <div className="bg-white rounded-xl shadow-lg p-6 mb-8">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-5 w-5" />
            <input
              type="text"
              placeholder="Search colleges..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
          <div className="relative">
            <Filter className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-5 w-5" />
            <select
              value={filterType}
              onChange={(e) => setFilterType(e.target.value)}
              className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 appearance-none"
            >
              <option value="All">All Types</option>
              <option value="Government">Government</option>
              <option value="Private">Private</option>
              <option value="Autonomous">Autonomous</option>
            </select>
          </div>
          <button className="bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 transition-colors">
            Find Near Me
          </button>
        </div>
      </div>

      {/* College List */}
      <div className="grid grid-cols-1 gap-6">
        {filteredColleges.map((college) => (
          <div key={college.id} className="bg-white rounded-xl shadow-lg border border-gray-200 overflow-hidden hover:shadow-xl transition-shadow">
            <div className="p-6">
              <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between">
                <div className="flex-1 mb-4 lg:mb-0">
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <h3 className="text-xl font-semibold text-gray-900 mb-1">{college.name}</h3>
                      <div className="flex items-center space-x-4 text-sm text-gray-500">
                        <div className="flex items-center">
                          <MapPin className="h-4 w-4 mr-1" />
                          {college.location}
                        </div>
                        <div className="flex items-center">
                          <Star className="h-4 w-4 mr-1 text-yellow-500" />
                          {college.rating}
                        </div>
                        <span className={`px-2 py-1 rounded-full text-xs ${
                          college.type === 'Government' ? 'bg-green-100 text-green-800' :
                          college.type === 'Private' ? 'bg-blue-100 text-blue-800' :
                          'bg-purple-100 text-purple-800'
                        }`}>
                          {college.type}
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
                    <div className="bg-gray-50 rounded-lg p-4">
                      <div className="flex items-center mb-2">
                        <Users className="h-4 w-4 text-gray-500 mr-2" />
                        <span className="font-medium text-gray-700">Courses</span>
                      </div>
                      <div className="space-y-1">
                        {college.courses.slice(0, 3).map((course, idx) => (
                          <div key={idx} className="text-sm text-gray-600">{course}</div>
                        ))}
                        {college.courses.length > 3 && (
                          <div className="text-sm text-blue-600">+{college.courses.length - 3} more</div>
                        )}
                      </div>
                    </div>

                    <div className="bg-gray-50 rounded-lg p-4">
                      <div className="flex items-center mb-2">
                        <BookOpen className="h-4 w-4 text-gray-500 mr-2" />
                        <span className="font-medium text-gray-700">Details</span>
                      </div>
                      <div className="space-y-1 text-sm text-gray-600">
                        <div>Fees: {college.fees}</div>
                        <div>Cutoff: {college.cutoff}</div>
                        <div>Distance: {college.distance}</div>
                      </div>
                    </div>

                    <div className="bg-gray-50 rounded-lg p-4">
                      <div className="flex items-center mb-2">
                        <Phone className="h-4 w-4 text-gray-500 mr-2" />
                        <span className="font-medium text-gray-700">Contact</span>
                      </div>
                      <div className="space-y-1 text-sm text-gray-600">
                        <div>{college.contact.phone}</div>
                        <div className="flex items-center text-blue-600 hover:text-blue-700">
                          <Globe className="h-3 w-3 mr-1" />
                          Website
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="flex flex-wrap gap-2">
                    {college.facilities.map((facility, idx) => (
                      <span
                        key={idx}
                        className="px-3 py-1 bg-blue-100 text-blue-800 text-sm rounded-full"
                      >
                        {facility}
                      </span>
                    ))}
                  </div>
                </div>

                <div className="lg:ml-6 flex flex-col space-y-2">
                  <button className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 transition-colors">
                    View Details
                  </button>
                  <button className="border border-gray-300 text-gray-700 px-6 py-2 rounded-lg hover:bg-gray-50 transition-colors">
                    Save College
                  </button>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Map Section */}
      <div className="mt-8 bg-white rounded-xl shadow-lg p-6">
        <h3 className="text-xl font-semibold mb-4">College Locations</h3>
        <div className="h-96 bg-gray-100 rounded-lg flex items-center justify-center">
          <div className="text-center">
            <MapPin className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <p className="text-gray-500">Interactive map integration would appear here</p>
            <p className="text-sm text-gray-400 mt-2">
              Map showing {filteredColleges.length} colleges in your area
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};