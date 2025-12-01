import { NextRequest, NextResponse } from 'next/server';
import { spawn } from 'child_process';
import path from 'path';
import { config } from '@/lib/config';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { action, catalog, schema, prompt_path } = body;

    // Prepare input data for Python script
    const inputData = {
      action: action || "search",
      catalog: config.lakemeterCatalog || "users",
      schema: config.lakemeterSchema || "fajar_muharandy",
      prompt_path: prompt_path || "",
    };

    // Path to Python script
    const scriptPath = path.join(process.cwd(), 'api_backend', 'prompt_service.py');

    // Execute Python script using spawn for better control over stdin/stdout
    const result = await new Promise<any>((resolve, reject) => {
      const pythonProcess = spawn(config.pythonPath, [scriptPath]);

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
