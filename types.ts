
export interface Message {
  role: 'user' | 'model';
  text: string;
}

export interface StoryState {
  image: string | null;
  mimeType: string | null;
  analysis: string;
  openingParagraph: string;
  isGenerating: boolean;
  error: string | null;
}

export interface ChatState {
  messages: Message[];
  isTyping: boolean;
}

export interface AudioState {
  isPlaying: boolean;
  isLoading: boolean;
}
