import { useState, useCallback } from 'react';
import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

/**
 * Custom hook for interacting with the Check-It AI API
 *
 * Handles:
 * - Sending queries to /api/chat
 * - Loading states (searching, analyzing, writing)
 * - Message history
 * - Error handling
 */
export const useCheckItAI = () => {
  const [messages, setMessages] = useState([]);
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

    // Simulate loading states
    setIsSearching(true);

    try {
      // Call the API
      const response = await axios.post(`${API_BASE_URL}/api/chat`, {
        query,
        mode,
      });

      // Transition through loading states
      setIsSearching(false);
      setIsAnalyzing(true);

      // Simulate analyzing delay
      await new Promise(resolve => setTimeout(resolve, 500));

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
        metadata: response.data.metadata,
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
    if (isSearching) return 'Searching sources...';
    if (isAnalyzing) return 'Analyzing evidence...';
    if (isWriting) return 'Writing response...';
    return null;
  }, [isSearching, isAnalyzing, isWriting]);

  return {
    messages,
    isLoading: isSearching || isAnalyzing || isWriting,
    isSearching,
    isAnalyzing,
    isWriting,
    error,
    currentEvidence,
    sendQuery,
    clearMessages,
    getLoadingMessage,
  };
};
