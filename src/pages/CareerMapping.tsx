import React, { useState } from 'react';
import { 
  TrendingUp, 
  BookOpen, 
  Award, 
  DollarSign,
  Users,
  Clock,
  Target,
  BarChart3
} from 'lucide-react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement,
} from 'chart.js';
import { Line, Bar, Doughnut } from 'react-chartjs-2';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement
);

export const CareerMapping: React.FC = () => {
  const [selectedStream, setSelectedStream] = useState('engineering');

  const streams = {
    engineering: {
      name: 'Engineering & Technology',
      careers: [
        { name: 'Software Engineer', salary: '₹8-15 LPA', growth: 'High', demand: 95 },
        { name: 'Data Scientist', salary: '₹10-20 LPA', growth: 'Very High', demand: 90 },
        { name: 'AI/ML Engineer', salary: '₹12-25 LPA', growth: 'Extremely High', demand: 88 },
        { name: 'Cybersecurity Analyst', salary: '₹9-18 LPA', growth: 'High', demand: 85 }
      ],
      exams: ['JEE Main', 'JEE Advanced', 'BITSAT', 'VITEEE'],
      skills: ['Programming', 'Mathematics', 'Problem Solving', 'Analytics']
    },
    medical: {
      name: 'Medical & Healthcare',
      careers: [
        { name: 'Doctor (MBBS)', salary: '₹8-20 LPA', growth: 'Stable', demand: 92 },
        { name: 'Pharmacist', salary: '₹4-8 LPA', growth: 'Moderate', demand: 78 },
        { name: 'Physiotherapist', salary: '₹3-7 LPA', growth: 'High', demand: 82 },
        { name: 'Medical Researcher', salary: '₹6-15 LPA', growth: 'High', demand: 75 }
      ],
      exams: ['NEET UG', 'NEET PG', 'AIIMS', 'JIPMER'],
      skills: ['Biology', 'Chemistry', 'Empathy', 'Communication']
    },
    commerce: {
      name: 'Commerce & Business',
      careers: [
        { name: 'Chartered Accountant', salary: '₹7-15 LPA', growth: 'Stable', demand: 88 },
        { name: 'Investment Banker', salary: '₹10-25 LPA', growth: 'High', demand: 80 },
        { name: 'Digital Marketer', salary: '₹5-12 LPA', growth: 'Very High', demand: 85 },
        { name: 'Business Analyst', salary: '₹8-16 LPA', growth: 'High', demand: 82 }
      ],
      exams: ['CA Foundation', 'CMA', 'CS Foundation', 'CLAT'],
      skills: ['Mathematics', 'Communication', 'Analytics', 'Leadership']
    }
  };

  const salaryTrendData = {
    labels: ['0-2 years', '2-5 years', '5-10 years', '10+ years'],
    datasets: [
      {
        label: 'Average Salary (LPA)',
        data: [6, 12, 20, 35],
        borderColor: 'rgb(59, 130, 246)',
        backgroundColor: 'rgba(59, 130, 246, 0.1)',
        tension: 0.3
      }
    ]
  };

  const demandData = {
    labels: streams[selectedStream as keyof typeof streams].careers.map(c => c.name),
    datasets: [
      {
        label: 'Industry Demand (%)',
        data: streams[selectedStream as keyof typeof streams].careers.map(c => c.demand),
        backgroundColor: [
          'rgba(59, 130, 246, 0.8)',
          'rgba(16, 185, 129, 0.8)',
          'rgba(139, 92, 246, 0.8)',
          'rgba(245, 158, 11, 0.8)'
        ],
        borderColor: [
          'rgb(59, 130, 246)',
          'rgb(16, 185, 129)',
          'rgb(139, 92, 246)',
          'rgb(245, 158, 11)'
        ],
        borderWidth: 1
      }
    ]
  };

  const skillsData = {
    labels: streams[selectedStream as keyof typeof streams].skills,
    datasets: [
      {
        data: [85, 78, 92, 80],
        backgroundColor: [
          'rgba(59, 130, 246, 0.8)',
          'rgba(16, 185, 129, 0.8)',
          'rgba(139, 92, 246, 0.8)',
          'rgba(245, 158, 11, 0.8)'
        ],
        borderWidth: 2,
        borderColor: '#ffffff'
      }
    ]
  };

  const currentStream = streams[selectedStream as keyof typeof streams];

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <div className="text-center mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Career Mapping Dashboard</h1>
        <p className="text-gray-600">Explore career opportunities and pathways for different streams</p>
      </div>

      {/* Stream Selection */}
      <div className="bg-white rounded-xl shadow-lg p-6 mb-8">
        <h2 className="text-xl font-semibold mb-4">Select Stream</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {Object.entries(streams).map(([key, stream]) => (
            <button
              key={key}
              onClick={() => setSelectedStream(key)}
              className={`p-4 rounded-lg border-2 transition-all ${
                selectedStream === key
                  ? 'border-blue-500 bg-blue-50 text-blue-700'
                  : 'border-gray-200 hover:border-blue-300 hover:bg-blue-25'
              }`}
            >
              <h3 className="font-semibold">{stream.name}</h3>
            </button>
          ))}
        </div>
      </div>

      {/* Career Options */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
        <div className="bg-white rounded-xl shadow-lg p-6">
          <h3 className="text-xl font-semibold mb-4 flex items-center">
            <Target className="h-5 w-5 text-blue-600 mr-2" />
            Career Opportunities
          </h3>
          <div className="space-y-4">
            {currentStream.careers.map((career, index) => (
              <div key={index} className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow">
                <div className="flex justify-between items-start mb-2">
                  <h4 className="font-medium text-gray-900">{career.name}</h4>
                  <span className="text-sm text-green-600 font-medium">{career.salary}</span>
                </div>
                <div className="flex items-center space-x-4 text-sm text-gray-500">
                  <span className="flex items-center">
                    <TrendingUp className="h-4 w-4 mr-1" />
                    {career.growth}
                  </span>
                  <span className="flex items-center">
                    <Users className="h-4 w-4 mr-1" />
                    {career.demand}% demand
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white rounded-xl shadow-lg p-6">
          <h3 className="text-xl font-semibold mb-4 flex items-center">
            <BarChart3 className="h-5 w-5 text-green-600 mr-2" />
            Industry Demand
          </h3>
          <Bar 
            data={demandData}
            options={{
              responsive: true,
              plugins: {
                legend: {
                  display: false
                }
              },
              scales: {
                y: {
                  beginAtZero: true,
                  max: 100
                }
              }
            }}
          />
        </div>
      </div>

      {/* Skills & Growth */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
        <div className="bg-white rounded-xl shadow-lg p-6">
          <h3 className="text-xl font-semibold mb-4 flex items-center">
            <Award className="h-5 w-5 text-purple-600 mr-2" />
            Key Skills Required
          </h3>
          <Doughnut 
            data={skillsData}
            options={{
              responsive: true,
              plugins: {
                legend: {
                  position: 'bottom' as const,
                }
              }
            }}
          />
        </div>

        <div className="bg-white rounded-xl shadow-lg p-6">
          <h3 className="text-xl font-semibold mb-4 flex items-center">
            <DollarSign className="h-5 w-5 text-green-600 mr-2" />
            Salary Growth Trend
          </h3>
          <Line 
            data={salaryTrendData}
            options={{
              responsive: true,
              plugins: {
                legend: {
                  display: false
                }
              },
              scales: {
                y: {
                  beginAtZero: true
                }
              }
            }}
          />
        </div>
      </div>

      {/* Exams & Requirements */}
      <div className="bg-white rounded-xl shadow-lg p-6">
        <h3 className="text-xl font-semibold mb-4 flex items-center">
          <BookOpen className="h-5 w-5 text-orange-600 mr-2" />
          Required Exams & Preparations
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <h4 className="font-medium text-gray-900 mb-3">Entrance Exams</h4>
            <div className="space-y-2">
              {currentStream.exams.map((exam, index) => (
                <div key={index} className="flex items-center space-x-3 p-3 bg-gray-50 rounded-lg">
                  <div className="w-2 h-2 bg-blue-600 rounded-full"></div>
                  <span className="text-gray-700">{exam}</span>
                  <span className="text-sm text-gray-500 ml-auto">Learn More</span>
                </div>
              ))}
            </div>
          </div>
          <div>
            <h4 className="font-medium text-gray-900 mb-3">Essential Skills</h4>
            <div className="space-y-2">
              {currentStream.skills.map((skill, index) => (
                <div key={index} className="flex items-center space-x-3 p-3 bg-gray-50 rounded-lg">
                  <div className="w-2 h-2 bg-green-600 rounded-full"></div>
                  <span className="text-gray-700">{skill}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};