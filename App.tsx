
import React, { useState, useRef, useCallback } from 'react';
import { StoryState, ChatState, AudioState, Message } from './types';
import { analyzeAndGenerateStory, chatWithGemini, generateSpeech, decodeBase64ToUint8Array, decodeAudioData } from './services/geminiService';
import { Button } from './components/Button';
import { ChatWindow } from './components/ChatWindow';

const App: React.FC = () => {
  const [story, setStory] = useState<StoryState>({
    image: null,
    mimeType: null,
    analysis: '',
    openingParagraph: '',
    isGenerating: false,
    error: null,
  });

  const [chat, setChat] = useState<ChatState>({
    messages: [],
    isTyping: false,
  });

  const [audio, setAudio] = useState<AudioState>({
    isPlaying: false,
    isLoading: false,
  });

  const audioContextRef = useRef<AudioContext | null>(null);
  const audioSourceRef = useRef<AudioBufferSourceNode | null>(null);

  const handleImageUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onloadend = async () => {
      const base64 = (reader.result as string).split(',')[1];
      const mimeType = file.type;
      
      setStory(prev => ({ 
        ...prev, 
        image: base64, 
        mimeType, 
        isGenerating: true, 
        error: null,
        openingParagraph: '',
        analysis: ''
      }));
      setChat({ messages: [], isTyping: false });

      try {
        const result = await analyzeAndGenerateStory(base64, mimeType);
        setStory(prev => ({
          ...prev,
          isGenerating: false,
          analysis: result.analysis,
          openingParagraph: result.opening
        }));
      } catch (err: any) {
        setStory(prev => ({ ...prev, isGenerating: false, error: "Failed to analyze image. Please try again." }));
        console.error(err);
      }
    };
    reader.readAsDataURL(file);
  };

  const handleSendMessage = async (text: string) => {
    const newUserMsg: Message = { role: 'user', text };
    setChat(prev => ({ ...prev, messages: [...prev.messages, newUserMsg], isTyping: true }));

    try {
      const response = await chatWithGemini(chat.messages, text);
      const botMsg: Message = { role: 'model', text: response };
      setChat(prev => ({ ...prev, messages: [...prev.messages, botMsg], isTyping: false }));
    } catch (err) {
      console.error(err);
      setChat(prev => ({ ...prev, isTyping: false }));
    }
  };

  const togglePlayback = async () => {
    if (audio.isPlaying) {
      audioSourceRef.current?.stop();
      setAudio({ isPlaying: false, isLoading: false });
      return;
    }

    if (!story.openingParagraph) return;

    setAudio(prev => ({ ...prev, isLoading: true }));
    try {
      if (!audioContextRef.current) {
        audioContextRef.current = new (window.AudioContext || (window as any).webkitAudioContext)({ sampleRate: 24000 });
      }
      
      const base64Audio = await generateSpeech(story.openingParagraph);
      const audioData = decodeBase64ToUint8Array(base64Audio);
      const audioBuffer = await decodeAudioData(audioData, audioContextRef.current);
      
      const source = audioContextRef.current.createBufferSource();
      source.buffer = audioBuffer;
      source.connect(audioContextRef.current.destination);
      
      source.onended = () => {
        setAudio({ isPlaying: false, isLoading: false });
      };

      audioSourceRef.current = source;
      source.start(0);
      setAudio({ isPlaying: true, isLoading: false });
    } catch (err) {
      console.error(err);
      setAudio({ isPlaying: false, isLoading: false });
    }
  };

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="px-6 py-4 bg-slate-900 border-b border-slate-800 flex items-center justify-between sticky top-0 z-50">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-indigo-600 rounded-xl flex items-center justify-center shadow-lg shadow-indigo-500/20">
            <i className="fas fa-feather-pointed text-white text-xl"></i>
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight">MuseScape</h1>
            <p className="text-[10px] text-slate-400 uppercase tracking-widest font-semibold">AI Creative Writing Studio</p>
          </div>
        </div>
        
        {story.image && (
          <div className="hidden sm:block">
             <label className="cursor-pointer">
                <span className="text-sm text-indigo-400 hover:text-indigo-300 transition-colors font-medium">
                  <i className="fas fa-upload mr-2"></i>New Scene
                </span>
                <input type="file" className="hidden" accept="image/*" onChange={handleImageUpload} />
             </label>
          </div>
        )}
      </header>

      <main className="flex-1 flex flex-col md:flex-row p-4 md:p-6 gap-6 max-w-7xl mx-auto w-full">
        {/* Left Column: Image Area */}
        <div className="flex-1 space-y-6">
          <div className="aspect-video w-full bg-slate-800 rounded-3xl overflow-hidden border border-slate-700 relative shadow-2xl group">
            {!story.image ? (
              <label className="absolute inset-0 flex flex-col items-center justify-center cursor-pointer hover:bg-slate-700/50 transition-all">
                <div className="w-16 h-16 bg-slate-900/50 rounded-full flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                  <i className="fas fa-image text-slate-500 text-2xl"></i>
                </div>
                <p className="text-slate-300 font-medium">Upload an image to start</p>
                <p className="text-slate-500 text-sm mt-1">Drag and drop or click to browse</p>
                <input type="file" className="hidden" accept="image/*" onChange={handleImageUpload} />
              </label>
            ) : (
              <>
                <img 
                  src={`data:${story.mimeType};base64,${story.image}`} 
                  alt="Story reference" 
                  className="w-full h-full object-cover"
                />
                {story.isGenerating && (
                  <div className="absolute inset-0 bg-slate-950/60 backdrop-blur-sm flex flex-col items-center justify-center text-center p-6">
                    <i className="fas fa-sparkles fa-spin text-4xl text-indigo-400 mb-4"></i>
                    <h3 className="text-xl font-bold">Dreaming up the story...</h3>
                    <p className="text-slate-400 max-w-xs mt-2">Gemini is analyzing the mood and ghostwriting your opening paragraph.</p>
                  </div>
                )}
              </>
            )}
          </div>

          {story.analysis && (
            <div className="bg-slate-900/50 border border-slate-800 p-5 rounded-2xl animate-in fade-in slide-in-from-bottom-4 duration-500">
              <h4 className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-3">Analysis of Scene</h4>
              <p className="text-slate-300 text-sm italic leading-relaxed">
                "{story.analysis}"
              </p>
            </div>
          )}
        </div>

        {/* Right Column: Text and Chat */}
        <div className="flex-1 flex flex-col gap-6 h-full">
          {/* Story Passage */}
          <div className="flex-1 bg-slate-900 border border-slate-800 rounded-3xl p-6 md:p-8 flex flex-col shadow-xl min-h-[400px]">
            <div className="flex items-center justify-between mb-6">
              <span className="px-3 py-1 bg-indigo-500/10 text-indigo-400 text-[10px] font-bold uppercase tracking-widest rounded-full border border-indigo-500/20">
                Opening Passage
              </span>
              {story.openingParagraph && (
                <Button 
                  variant="ghost" 
                  size="sm" 
                  onClick={togglePlayback}
                  isLoading={audio.isLoading}
                  icon={audio.isPlaying ? "fas fa-stop" : "fas fa-volume-up"}
                  className={audio.isPlaying ? "text-rose-400 hover:text-rose-300" : ""}
                >
                  {audio.isPlaying ? "Stop Narration" : "Read Aloud"}
                </Button>
              )}
            </div>

            <div className="flex-1 relative">
              {story.openingParagraph ? (
                <div className="serif-font text-lg md:text-xl leading-loose text-slate-200 animate-in fade-in duration-1000">
                   {story.openingParagraph}
                   <span className="inline-block w-1.5 h-1.5 bg-indigo-500 ml-2 animate-pulse"></span>
                </div>
              ) : !story.isGenerating ? (
                <div className="h-full flex flex-col items-center justify-center text-slate-500 space-y-4">
                  <i className="fas fa-pen-nib text-3xl opacity-20"></i>
                  <p className="text-sm">Your story will appear here once an image is uploaded.</p>
                </div>
              ) : null}
            </div>

            {story.error && (
              <div className="mt-4 p-4 bg-rose-500/10 border border-rose-500/20 text-rose-400 text-sm rounded-xl flex items-center gap-3">
                <i className="fas fa-circle-exclamation"></i>
                {story.error}
              </div>
            )}
          </div>

          {/* Chat Window */}
          <div className="h-[350px]">
            <ChatWindow 
              messages={chat.messages} 
              onSendMessage={handleSendMessage} 
              isTyping={chat.isTyping} 
            />
          </div>
        </div>
      </main>

      <footer className="py-6 text-center text-slate-600 text-xs border-t border-slate-900 bg-slate-950">
        <p>&copy; 2024 MuseScape AI. Crafted with Gemini 3 Pro.</p>
      </footer>
    </div>
  );
};

export default App;
