import { NextRequest, NextResponse } from 'next/server';
import { spawn } from 'child_process';
import path from 'path';
import { config } from '@/lib/config';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { prompt_text } = body;

    if (!prompt_text) {
      return NextResponse.json(
        { success: false, error: 'prompt_text is required' },
        { status: 400 }
      );
    }

    // if (!config.anthropicApiKey) {
    //   return NextResponse.json(
    //     { success: false, error: 'Anthropic API key is not configured' },
    //     { status: 500 }
    //   );
    // }

    if (!config.openaiApiKey) {
      return NextResponse.json(
        { success: false, error: 'OpenAI API key is not configured' },
        { status: 500 }
      );
    }

    // Prepare input data for Python script
    const inputData = {
      prompt_text: prompt_text,
      system_prompt: config.systemPrompt,
      // api_key: config.anthropicApiKey, // Anthropic
      api_key: config.openaiApiKey, // OpenAI
      base_url: config.openaiBaseUrl, // OpenAI Base URL (optional)
    };

    // Path to Python script
    // const scriptPath = path.join(process.cwd(), 'api_backend', 'anthropic_service.py'); // Anthropic
    const scriptPath = path.join(process.cwd(), 'api_backend', 'openai_service.py'); // OpenAI

    // Execute Python script using spawn for better control over stdin/stdout
    const result = await new Promise<any>((resolve, reject) => {
      const pythonProcess = spawn('python3', [scriptPath]);
      
      let stdout = '';
      let stderr = '';

      // Send JSON data to Python script's stdin
      pythonProcess.stdin.write(JSON.stringify(inputData));
      pythonProcess.stdin.end();

      // Collect stdout
      pythonProcess.stdout.on('data', (data) => {
        stdout += data.toString();
      });

      // Collect stderr
      pythonProcess.stderr.on('data', (data) => {
        stderr += data.toString();
      });

      // Handle process completion
      pythonProcess.on('close', (code) => {
        if (stderr) {
          console.error('Python script stderr:', stderr);
        }

        if (code !== 0) {
          reject(new Error(`Python script exited with code ${code}: ${stderr}`));
          return;
        }

        try {
          const parsedResult = JSON.parse(stdout);
          resolve(parsedResult);
        } catch (parseError) {
          reject(new Error(`Failed to parse Python output: ${stdout}`));
        }
      });

      pythonProcess.on('error', (error) => {
        reject(error);
      });
    });

    if (result.success) {
      return NextResponse.json(result, { status: 200 });
    } else {
      return NextResponse.json(result, { status: 500 });
    }
  } catch (error) {
    console.error('Error calling Python API:', error);
    return NextResponse.json(
      {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error occurred',
      },
      { status: 500 }
    );
  }
}
