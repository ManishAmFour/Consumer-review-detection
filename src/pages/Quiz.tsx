import React, { useState } from 'react';
import { Brain, ChevronRight, CheckCircle, RotateCcw } from 'lucide-react';

interface Question {
  id: number;
  question: string;
  options: string[];
  category: 'logical' | 'verbal' | 'numerical' | 'spatial';
}

export const Quiz: React.FC = () => {
  const [currentQuestion, setCurrentQuestion] = useState(0);
  const [answers, setAnswers] = useState<{ [key: number]: number }>({});
  const [showResults, setShowResults] = useState(false);

  const questions: Question[] = [
    {
      id: 1,
      question: "Which of the following best describes your problem-solving approach?",
      options: [
        "I prefer breaking down complex problems into smaller, manageable parts",
        "I like to visualize problems and think in patterns",
        "I enjoy working with numbers and data analysis",
        "I prefer discussing problems with others and exploring different perspectives"
      ],
      category: 'logical'
    },
    {
      id: 2,
      question: "What type of activities do you find most engaging?",
      options: [
        "Building or creating things with my hands",
        "Reading and writing about various topics",
        "Conducting experiments and research",
        "Organizing events and leading teams"
      ],
      category: 'verbal'
    },
    {
      id: 3,
      question: "In a group project, you typically:",
      options: [
        "Take charge and coordinate the team",
        "Focus on research and analysis",
        "Handle the creative and design aspects",
        "Ensure everyone stays on track with deadlines"
      ],
      category: 'spatial'
    },
    {
      id: 4,
      question: "Which subject area interests you most?",
      options: [
        "Mathematics and Statistics",
        "Literature and Languages",
        "Science and Technology",
        "Arts and Design"
      ],
      category: 'numerical'
    },
    {
      id: 5,
      question: "Your ideal work environment would be:",
      options: [
        "A collaborative office with team interactions",
        "A quiet space for focused, independent work",
        "A dynamic environment with varied challenges",
        "A creative studio or workshop setting"
      ],
      category: 'spatial'
    }
  ];

  const handleAnswer = (optionIndex: number) => {
    setAnswers({ ...answers, [currentQuestion]: optionIndex });
  };

  const nextQuestion = () => {
    if (currentQuestion < questions.length - 1) {
      setCurrentQuestion(currentQuestion + 1);
    } else {
      setShowResults(true);
    }
  };

  const resetQuiz = () => {
    setCurrentQuestion(0);
    setAnswers({});
    setShowResults(false);
  };

  const getResults = () => {
    const categories = {
      logical: 0,
      verbal: 0,
      numerical: 0,
      spatial: 0
    };

    Object.entries(answers).forEach(([questionIndex, answerIndex]) => {
      const question = questions[parseInt(questionIndex)];
      categories[question.category]++;
    });

    const maxCategory = Object.entries(categories).reduce((a, b) => 
      categories[a[0] as keyof typeof categories] > categories[b[0] as keyof typeof categories] ? a : b
    );

    const recommendations = {
      logical: {
        stream: "Engineering & Technology",
        careers: ["Software Engineer", "Data Scientist", "Systems Analyst"],
        description: "Your logical thinking and problem-solving skills align well with technical fields."
      },
      verbal: {
        stream: "Humanities & Liberal Arts",
        careers: ["Content Writer", "Journalist", "Teacher", "Lawyer"],
        description: "Your communication and language skills suggest success in humanities fields."
      },
      numerical: {
        stream: "Science & Mathematics",
        careers: ["Research Scientist", "Statistician", "Financial Analyst"],
        description: "Your quantitative abilities indicate strong potential in science and mathematics."
      },
      spatial: {
        stream: "Creative & Design",
        careers: ["Architect", "Graphic Designer", "UX Designer"],
        description: "Your spatial reasoning suggests talent in creative and design fields."
      }
    };

    return recommendations[maxCategory[0] as keyof typeof recommendations];
  };

  if (showResults) {
    const result = getResults();
    
    return (
      <div className="max-w-4xl mx-auto px-4 py-8">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-green-100 rounded-full mb-4">
            <CheckCircle className="h-8 w-8 text-green-600" />
          </div>
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Assessment Complete!</h1>
          <p className="text-gray-600">Here are your personalized recommendations</p>
        </div>

        <div className="bg-white rounded-xl shadow-lg p-8 mb-8">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">Recommended Stream</h2>
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-6 mb-6">
            <h3 className="text-xl font-semibold text-blue-900 mb-2">{result.stream}</h3>
            <p className="text-blue-700">{result.description}</p>
          </div>

          <h3 className="text-lg font-semibold text-gray-900 mb-4">Potential Career Paths</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            {result.careers.map((career, index) => (
              <div key={index} className="bg-gray-50 rounded-lg p-4 text-center">
                <p className="font-medium text-gray-900">{career}</p>
              </div>
            ))}
          </div>

          <div className="flex space-x-4">
            <button
              onClick={resetQuiz}
              className="flex items-center space-x-2 px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 transition-colors"
            >
              <RotateCcw className="h-4 w-4" />
              <span>Retake Quiz</span>
            </button>
            <button className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 transition-colors">
              View Detailed Report
            </button>
          </div>
        </div>
      </div>
    );
  }

  const progress = ((currentQuestion + 1) / questions.length) * 100;

  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      <div className="text-center mb-8">
        <div className="inline-flex items-center justify-center w-16 h-16 bg-blue-100 rounded-full mb-4">
          <Brain className="h-8 w-8 text-blue-600" />
        </div>
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Aptitude Assessment</h1>
        <p className="text-gray-600">Discover your strengths and ideal career path</p>
      </div>

      <div className="bg-white rounded-xl shadow-lg p-8">
        <div className="mb-8">
          <div className="flex justify-between items-center mb-2">
            <span className="text-sm font-medium text-gray-500">
              Question {currentQuestion + 1} of {questions.length}
            </span>
            <span className="text-sm font-medium text-blue-600">
              {Math.round(progress)}% Complete
            </span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div 
              className="bg-blue-600 h-2 rounded-full transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>

        <div className="mb-8">
          <h2 className="text-xl font-semibold text-gray-900 mb-6">
            {questions[currentQuestion].question}
          </h2>
          
          <div className="space-y-3">
            {questions[currentQuestion].options.map((option, index) => (
              <button
                key={index}
                onClick={() => handleAnswer(index)}
                className={`w-full text-left p-4 border rounded-lg transition-all duration-200 ${
                  answers[currentQuestion] === index
                    ? 'border-blue-500 bg-blue-50 text-blue-700'
                    : 'border-gray-200 hover:border-blue-300 hover:bg-blue-25'
                }`}
              >
                <div className="flex items-center space-x-3">
                  <div className={`w-4 h-4 rounded-full border-2 flex items-center justify-center ${
                    answers[currentQuestion] === index
                      ? 'border-blue-500 bg-blue-500'
                      : 'border-gray-300'
                  }`}>
                    {answers[currentQuestion] === index && (
                      <div className="w-2 h-2 bg-white rounded-full" />
                    )}
                  </div>
                  <span className="flex-1">{option}</span>
                </div>
              </button>
            ))}
          </div>
        </div>

        <div className="flex justify-end">
          <button
            onClick={nextQuestion}
            disabled={answers[currentQuestion] === undefined}
            className="flex items-center space-x-2 bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <span>{currentQuestion === questions.length - 1 ? 'Get Results' : 'Next'}</span>
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );
};