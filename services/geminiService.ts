
import { GoogleGenAI, Modality, Type } from "@google/genai";

const getAI = () => new GoogleGenAI({ apiKey: process.env.API_KEY || '' });

export const analyzeAndGenerateStory = async (base64Image: string, mimeType: string) => {
  const ai = getAI();
  const prompt = `Analyze this image in detail. Identify the mood, lighting, key subjects, and setting. 
  Then, write an evocative, atmospheric opening paragraph (approx 100-150 words) for a story set in this exact scene. 
  The tone should match the visual style. 
  
  Return the response as a JSON object with two fields:
  "analysis": A brief summary of the scene's mood and elements.
  "opening": The creative writing piece.`;

  const response = await ai.models.generateContent({
    model: 'gemini-3-pro-preview',
    contents: {
      parts: [
        { inlineData: { data: base64Image, mimeType } },
        { text: prompt }
      ]
    },
    config: {
      responseMimeType: "application/json",
      responseSchema: {
        type: Type.OBJECT,
        properties: {
          analysis: { type: Type.STRING },
          opening: { type: Type.STRING }
        },
        required: ["analysis", "opening"]
      }
    }
  });

  return JSON.parse(response.text || '{}');
};

export const chatWithGemini = async (history: { role: string; text: string }[], userMessage: string, contextImage?: { data: string; mimeType: string }) => {
  const ai = getAI();
  const chat = ai.chats.create({
    model: 'gemini-3-pro-preview',
    config: {
      systemInstruction: "You are MuseScape, a creative writing assistant. You help the user expand on the world shown in their image and the story started in the opening paragraph. Be descriptive, encouraging, and maintain the established mood.",
    }
  });

  // Since we use the chat object, we send messages one by one or reconstruct state
  // For simplicity in this demo, we'll just send the message. 
  // If we had context, we'd include the image in the first turn.
  
  const response = await chat.sendMessage({ message: userMessage });
  return response.text || "I'm sorry, I couldn't process that request.";
};

export const generateSpeech = async (text: string) => {
  const ai = getAI();
  const response = await ai.models.generateContent({
    model: "gemini-2.5-flash-preview-tts",
    contents: [{ parts: [{ text: `Read this story passage with deep emotion and atmosphere: ${text}` }] }],
    config: {
      responseModalities: [Modality.AUDIO],
      speechConfig: {
        voiceConfig: {
          prebuiltVoiceConfig: { voiceName: 'Kore' },
        },
      },
    },
  });

  const base64Audio = response.candidates?.[0]?.content?.parts?.[0]?.inlineData?.data;
  if (!base64Audio) throw new Error("No audio data returned");
  return base64Audio;
};

// Audio Utilities
export const decodeBase64ToUint8Array = (base64: string) => {
  const binaryString = atob(base64);
  const bytes = new Uint8Array(binaryString.length);
  for (let i = 0; i < binaryString.length; i++) {
    bytes[i] = binaryString.charCodeAt(i);
  }
  return bytes;
};

export const decodeAudioData = async (
  data: Uint8Array,
  ctx: AudioContext,
  sampleRate: number = 24000,
  numChannels: number = 1
): Promise<AudioBuffer> => {
  const dataInt16 = new Int16Array(data.buffer);
  const frameCount = dataInt16.length / numChannels;
  const buffer = ctx.createBuffer(numChannels, frameCount, sampleRate);

  for (let channel = 0; channel < numChannels; channel++) {
    const channelData = buffer.getChannelData(channel);
    for (let i = 0; i < frameCount; i++) {
      channelData[i] = dataInt16[i * numChannels + channel] / 32768.0;
    }
  }
  return buffer;
};
