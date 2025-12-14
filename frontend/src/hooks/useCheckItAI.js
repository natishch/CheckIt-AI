import { useState, useCallback } from 'react';
import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

/**
 * Pipeline step definitions for the Process Indicator
 */
export const PIPELINE_STEPS = {
  ROUTER: 'router',
  RESEARCHER: 'researcher',
  ANALYST: 'analyst',
  WRITER: 'writer',
};

/**
 * Custom hook for interacting with the Check-It AI API
 *
 * Handles:
 * - Sending queries to /api/chat
 * - Loading states with pipeline step tracking (router → researcher → analyst → writer)
 * - Message history with citations and evidence
 * - Error handling
 */
export const useCheckItAI = () => {
  const [messages, setMessages] = useState([]);
  const [isRouting, setIsRouting] = useState(false);
  const [isSearching, setIsSearching] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isWriting, setIsWriting] = useState(false);
  const [error, setError] = useState(null);
  const [currentEvidence, setCurrentEvidence] = useState(null);

  /**
   * Send a query to the API
   * @param {string} query - The user's query/claim to verify
   * @param {string} mode - Chat mode ('standard' for now)
   */
  const sendQuery = useCallback(async (query, mode = 'standard') => {
    if (!query.trim()) {
      setError('Query cannot be empty');
      return;
    }

    // Add user message to history
    const userMessage = {
      id: Date.now(),
      role: 'user',
      content: query,
      timestamp: new Date().toISOString(),
    };

    setMessages(prev => [...prev, userMessage]);
    setError(null);

    // Step 1: Router (brief initial state)
    setIsRouting(true);
    await new Promise(resolve => setTimeout(resolve, 200));
    setIsRouting(false);

    // Step 2: Researcher (API call happens here)
    setIsSearching(true);

    try {
      // Call the API
      const response = await axios.post(`${API_BASE_URL}/api/chat`, {
        query,
        mode,
      });

      // Step 3: Analyst
      setIsSearching(false);
      setIsAnalyzing(true);

      // Simulate analyzing delay
      await new Promise(resolve => setTimeout(resolve, 500));

      // Step 4: Writer
      setIsAnalyzing(false);
      setIsWriting(true);

      // Simulate writing delay
      await new Promise(resolve => setTimeout(resolve, 300));

      setIsWriting(false);

      // Add assistant response to history
      const assistantMessage = {
        id: Date.now() + 1,
        role: 'assistant',
        content: response.data.answer,
        citations: response.data.citations,
        evidence: response.data.evidence,
        route: response.data.route,
        metadata: {
          ...response.data.metadata,
          confidence: response.data.metadata?.confidence || 0,
          route: response.data.route,
        },
        timestamp: new Date().toISOString(),
      };

      setMessages(prev => [...prev, assistantMessage]);
      setCurrentEvidence(response.data.evidence);

    } catch (err) {
      console.error('API Error:', err);
      setError(err.response?.data?.detail || 'Failed to get response from API');

      // Add error message
      const errorMessage = {
        id: Date.now() + 1,
        role: 'error',
        content: err.response?.data?.detail || 'An error occurred. Please try again.',
        timestamp: new Date().toISOString(),
      };

      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsRouting(false);
      setIsSearching(false);
      setIsAnalyzing(false);
      setIsWriting(false);
    }
  }, []);

  /**
   * Clear all messages
   */
  const clearMessages = useCallback(() => {
    setMessages([]);
    setCurrentEvidence(null);
    setError(null);
  }, []);

  /**
   * Get loading state message
   */
  const getLoadingMessage = useCallback(() => {
    if (isRouting) return 'Routing query...';
    if (isSearching) return 'Searching sources...';
    if (isAnalyzing) return 'Analyzing evidence...';
    if (isWriting) return 'Writing response...';
    return null;
  }, [isRouting, isSearching, isAnalyzing, isWriting]);

  /**
   * Get current pipeline step
   */
  const getCurrentStep = useCallback(() => {
    if (isRouting) return PIPELINE_STEPS.ROUTER;
    if (isSearching) return PIPELINE_STEPS.RESEARCHER;
    if (isAnalyzing) return PIPELINE_STEPS.ANALYST;
    if (isWriting) return PIPELINE_STEPS.WRITER;
    return null;
  }, [isRouting, isSearching, isAnalyzing, isWriting]);

  /**
   * Get completed pipeline steps
   */
  const getCompletedSteps = useCallback(() => {
    const steps = [];
    if (isSearching) steps.push(PIPELINE_STEPS.ROUTER);
    if (isAnalyzing) steps.push(PIPELINE_STEPS.ROUTER, PIPELINE_STEPS.RESEARCHER);
    if (isWriting) steps.push(PIPELINE_STEPS.ROUTER, PIPELINE_STEPS.RESEARCHER, PIPELINE_STEPS.ANALYST);
    return [...new Set(steps)]; // Remove duplicates
  }, [isSearching, isAnalyzing, isWriting]);

  return {
    messages,
    isLoading: isRouting || isSearching || isAnalyzing || isWriting,
    isRouting,
    isSearching,
    isAnalyzing,
    isWriting,
    error,
    currentEvidence,
    sendQuery,
    clearMessages,
    getLoadingMessage,
    getCurrentStep,
    getCompletedSteps,
  };
};
