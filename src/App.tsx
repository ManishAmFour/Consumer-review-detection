import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { Header } from './components/Header';
import { Dashboard } from './pages/Dashboard';
import { Quiz } from './pages/Quiz';
import { CareerMapping } from './pages/CareerMapping';
import { Colleges } from './pages/Colleges';
import { Timeline } from './pages/Timeline';
import { Resources } from './pages/Resources';
import { Profile } from './pages/Profile';
import { Login } from './pages/Login';
import { Register } from './pages/Register';

function App() {
  return (
    <AuthProvider>
      <Router>
        <div className="min-h-screen bg-gray-50">
          <Header />
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route path="/quiz" element={<Quiz />} />
            <Route path="/career-mapping" element={<CareerMapping />} />
            <Route path="/colleges" element={<Colleges />} />
            <Route path="/timeline" element={<Timeline />} />
            <Route path="/resources" element={<Resources />} />
            <Route path="/profile" element={<Profile />} />
          </Routes>
        </div>
      </Router>
    </AuthProvider>
  );
}

export default App;