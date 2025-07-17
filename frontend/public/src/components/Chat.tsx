import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Send, ArrowLeft, Bot, User, Settings } from 'lucide-react';
import { QueryOutput } from './Result';
import Sidebar from './Sidebar';
import { DebugPanel } from './DebugPanel';
import { ApiService } from '../services/api';
import type { ChatMessage } from '../types/chat';
import type { QueryResult } from '../types/database';

interface ChatProps {
  initialQuery?: string;
}

const Chat: React.FC<ChatProps> = ({ initialQuery = '' }) => {
  const navigate = useNavigate();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [loadingStep, setLoadingStep] = useState('');
  const [showDebugPanel, setShowDebugPanel] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const lastProcessedQuery = useRef<string>('');

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    if (initialQuery && initialQuery !== lastProcessedQuery.current) {
      lastProcessedQuery.current = initialQuery;
      // Add the new query to the conversation (don't clear existing messages)
      handleSendMessage(initialQuery);
      setInputValue('');
    }
  }, [initialQuery]);

  const executeQuery = async (query: string): Promise<{ results?: QueryResult[], error?: string }> => {
    try {
      setLoadingStep('Analyzing your question...');
      // Add a small delay to show the step
      await new Promise(resolve => setTimeout(resolve, 100));
      
      setLoadingStep('Generating SQL query...');
      await new Promise(resolve => setTimeout(resolve, 100));
      
      setLoadingStep('Executing query...');
      
      // Use the real API service to execute natural language queries
      const result = await ApiService.executeNaturalLanguageQuery(query);
      
      setLoadingStep('Formatting results...');
      await new Promise(resolve => setTimeout(resolve, 200));
      
      return result;
    } catch (error) {
      console.error('Query execution error:', error);
      return {
        error: error instanceof Error ? error.message : 'An unexpected error occurred while executing the query'
      };
    } finally {
      setLoadingStep('');
    }
  };

  const handleSendMessage = async (messageContent: string = inputValue) => {
    if (!messageContent.trim()) return;

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      type: 'user',
      content: messageContent.trim(),
      timestamp: new Date(),
    };

    const loadingMessage: ChatMessage = {
      id: (Date.now() + 1).toString(),
      type: 'assistant',
      content: 'Processing your query...',
      timestamp: new Date(),
      isLoading: true,
    };

    setMessages(prev => [...prev, userMessage, loadingMessage]);
    setInputValue('');
    setIsLoading(true);

    try {
      const { results, error } = await executeQuery(messageContent);
      
      const assistantMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        type: 'assistant',
        content: error 
          ? 'I encountered an error while executing your query.' 
          : results && results.length > 0 
            ? `Found ${results[0].values.length} results for your query.`
            : 'Query executed successfully.',
        timestamp: new Date(),
        results,
        error,
      };

      setMessages(prev => prev.slice(0, -1).concat(assistantMessage));
    } catch (err) {
      const errorMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        type: 'assistant',
        content: 'An unexpected error occurred.',
        timestamp: new Date(),
        error: 'Connection failed',
      };

      setMessages(prev => prev.slice(0, -1).concat(errorMessage));
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const adjustTextareaHeight = () => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
    }
  };

  useEffect(() => {
    adjustTextareaHeight();
  }, [inputValue]);

  return (
    <div className="flex h-screen bg-white text-gray-900 overflow-hidden">
      {/* Sidebar */}
      <Sidebar />
      
      {/* Chat Interface */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <header className="bg-white border-b border-gray-200 px-6 py-4 flex items-center gap-4">
          <button
            onClick={() => navigate('/')}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <ArrowLeft className="w-5 h-5 text-gray-600" />
          </button>
          <div className="flex items-center gap-3">
            <div>
              <h1 className="font-semibold text-gray-900">Skyworks SQL Assistant</h1>
            </div>
          </div>
          <div className="ml-auto">
            <button
              onClick={() => setShowDebugPanel(true)}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
              title="Debug API Connection"
            >
              <Settings className="w-5 h-5 text-gray-600" />
            </button>
          </div>
        </header>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          <AnimatePresence>
            {messages.length === 0 && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="text-center py-12"
              >
                <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <Bot className="w-8 h-8" style={{ color: '#113D73' }} />
                </div>
                <h3 className="text-lg font-medium text-gray-900 mb-2">
                  Ready to help with your data queries
                </h3>
                <p className="text-gray-500">
                  Ask me anything about your database and I'll generate the SQL for you.
                </p>
              </motion.div>
            )}
            
            {messages.map((message) => (
              <motion.div
                key={message.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                className={`flex ${
                  message.type === 'user' ? 'justify-end' : 'justify-start'
                }`}
              >
                <div className="max-w-3xl">
                  <div
                    className={`rounded-2xl px-4 py-3 ${
                      message.type === 'user'
                        ? 'text-white'
                        : 'bg-white border border-gray-200'
                    }`}
                    style={message.type === 'user' ? { backgroundColor: '#113D73' } : {}}
                  >
                    <p className="whitespace-pre-wrap">
                      {message.isLoading ? (loadingStep || message.content) : message.content}
                    </p>
                    {message.isLoading && (
                      <div className="flex items-center gap-2 mt-2">
                        <div className="flex space-x-1">
                          <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:-0.3s]"></div>
                          <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:-0.15s]"></div>
                          <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                        </div>
                      </div>
                    )}
                  </div>
                  
                  {/* Query Results */}
                  {(message.results || message.error) && !message.isLoading && (
                    <div className="mt-4">
                      <QueryOutput
                        results={message.results || []}
                        error={message.error || ''}
                        onClose={() => {
                          // Remove the results from this message
                          setMessages(prev => prev.map(msg => 
                            msg.id === message.id 
                              ? { ...msg, results: undefined, error: undefined }
                              : msg
                          ));
                        }}
                      />
                    </div>
                  )}
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="border-t border-gray-200 bg-white p-4">
          <div className="flex items-center gap-4 max-w-4xl mx-auto">
            <div className="flex-1 relative">
              <textarea
                ref={textareaRef}
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask me about your data..."
                className="w-full px-4 py-3 border border-gray-200 rounded-xl resize-none focus:outline-none focus:ring-2 focus:border-transparent"
                style={{ 
                  minHeight: '48px', 
                  maxHeight: '120px'
                }}
                disabled={isLoading}
              />
            </div>
            
            <button
              onClick={() => handleSendMessage()}
              disabled={!inputValue.trim() || isLoading}
              className="px-4 py-3 text-white rounded-xl hover:opacity-90 focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex-shrink-0"
              style={{ 
                backgroundColor: '#113D73',
                height: '48px'
              }}
            >
              <Send className="w-5 h-5" />
            </button>
          </div>
        </div>
      </div>
      
      {/* Debug Panel */}
      {showDebugPanel && (
        <DebugPanel onClose={() => setShowDebugPanel(false)} />
      )}
    </div>
  );
};

export default Chat; 