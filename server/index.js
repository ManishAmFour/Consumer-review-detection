const express = require('express');
const cors = require('cors');
const path = require('path');
require('dotenv').config();

const app = express();
const PORT = process.env.PORT || 3001;

// Middleware
app.use(cors());
app.use(express.json());
app.use(express.static('dist'));

// AI Recommendation Service
const AIService = {
  generateRecommendations: (userProfile) => {
    // Mock AI algorithm for career recommendations
    const { interests, academicPerformance, stream, currentClass } = userProfile;
    
    const careerMappings = {
      'science-pcm': [
        { career: 'Software Engineer', match: 92, reason: 'Strong in mathematics and logical thinking' },
        { career: 'Data Scientist', match: 88, reason: 'Excellent analytical and mathematical skills' },
        { career: 'Mechanical Engineer', match: 85, reason: 'Good problem-solving and technical aptitude' }
      ],
      'science-pcb': [
        { career: 'Doctor', match: 95, reason: 'Strong in biology and committed to helping others' },
        { career: 'Research Scientist', match: 90, reason: 'Excellent research and analytical capabilities' },
        { career: 'Pharmacist', match: 82, reason: 'Good knowledge of chemistry and biology' }
      ],
      'commerce': [
        { career: 'Chartered Accountant', match: 88, reason: 'Strong mathematical and analytical skills' },
        { career: 'Investment Banker', match: 85, reason: 'Good with numbers and financial analysis' },
        { career: 'Business Analyst', match: 83, reason: 'Excellent analytical and communication skills' }
      ]
    };

    return careerMappings[stream] || careerMappings['science-pcm'];
  },

  analyzeQuizResults: (answers) => {
    // Mock quiz analysis
    const categories = {
      logical: 0,
      verbal: 0,
      numerical: 0,
      spatial: 0
    };

    // Simple scoring algorithm
    Object.values(answers).forEach((answer, index) => {
      const questionCategories = ['logical', 'verbal', 'spatial', 'numerical', 'spatial'];
      const category = questionCategories[index % questionCategories.length];
      categories[category]++;
    });

    const dominantCategory = Object.entries(categories).reduce((a, b) => 
      categories[a[0]] > categories[b[0]] ? a : b
    )[0];

    return {
      dominantSkill: dominantCategory,
      scores: categories,
      recommendations: this.generateRecommendations({ stream: dominantCategory })
    };
  }
};

// Routes

// AI Recommendations
app.post('/api/recommendations', (req, res) => {
  try {
    const { userProfile } = req.body;
    const recommendations = AIService.generateRecommendations(userProfile);
    
    res.json({
      success: true,
      recommendations,
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    res.status(500).json({ error: 'Failed to generate recommendations' });
  }
});

// Quiz Analysis
app.post('/api/quiz/analyze', (req, res) => {
  try {
    const { answers } = req.body;
    const analysis = AIService.analyzeQuizResults(answers);
    
    res.json({
      success: true,
      analysis,
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    res.status(500).json({ error: 'Failed to analyze quiz results' });
  }
});

// College Directory
app.get('/api/colleges', (req, res) => {
  try {
    const { location, type, course } = req.query;
    
    // Mock college data with filters
    let colleges = [
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

    // Apply filters
    if (type && type !== 'all') {
      colleges = colleges.filter(college => college.type.toLowerCase() === type.toLowerCase());
    }

    if (course) {
      colleges = colleges.filter(college => 
        college.courses.some(c => c.toLowerCase().includes(course.toLowerCase()))
      );
    }

    res.json({
      success: true,
      colleges,
      total: colleges.length
    });
  } catch (error) {
    res.status(500).json({ error: 'Failed to fetch colleges' });
  }
});

// Timeline Events
app.get('/api/timeline', (req, res) => {
  try {
    const events = [
      {
        id: 1,
        title: 'JEE Main Registration',
        description: 'Last date to register for JEE Main 2024',
        date: '2024-01-30',
        category: 'exam',
        status: 'urgent',
        daysLeft: 15
      },
      {
        id: 2,
        title: 'NEET Application',
        description: 'NEET UG 2024 application form submission',
        date: '2024-02-15',
        category: 'exam',
        status: 'upcoming',
        daysLeft: 31
      }
    ];

    res.json({
      success: true,
      events
    });
  } catch (error) {
    res.status(500).json({ error: 'Failed to fetch timeline events' });
  }
});

// Resources
app.get('/api/resources', (req, res) => {
  try {
    const { type, category } = req.query;
    
    let resources = [
      {
        id: 1,
        title: 'Complete Guide to JEE Main Preparation',
        type: 'ebook',
        category: 'Engineering',
        rating: 4.8,
        downloads: 15420,
        url: '#'
      },
      {
        id: 2,
        title: 'Data Science Fundamentals',
        type: 'course',
        category: 'Technology',
        rating: 4.9,
        downloads: 8750,
        url: '#'
      }
    ];

    // Apply filters
    if (type && type !== 'all') {
      resources = resources.filter(resource => resource.type === type);
    }

    if (category && category !== 'all') {
      resources = resources.filter(resource => resource.category === category);
    }

    res.json({
      success: true,
      resources,
      total: resources.length
    });
  } catch (error) {
    res.status(500).json({ error: 'Failed to fetch resources' });
  }
});

// Serve React app for all other routes
app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, '../dist/index.html'));
});

app.listen(PORT, () => {
  console.log(`🚀 EduGuide API Server running on port ${PORT}`);
  console.log(`📊 AI Recommendations: http://localhost:${PORT}/api/recommendations`);
  console.log(`🎯 Quiz Analysis: http://localhost:${PORT}/api/quiz/analyze`);
  console.log(`🏫 College Directory: http://localhost:${PORT}/api/colleges`);
  console.log(`📅 Timeline Events: http://localhost:${PORT}/api/timeline`);
  console.log(`📚 Resources: http://localhost:${PORT}/api/resources`);
});

module.exports = app;