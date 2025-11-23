// Configuration file for API settings
import { systemPrompt } from './system-prompt';

export const config = {
  // Anthropic API Key - Replace with your actual API key
  anthropicApiKey: process.env.NEXT_PUBLIC_ANTHROPIC_API_KEY || "",
  
  // System prompt that will be prepended to user input
  systemPrompt: systemPrompt,
};
