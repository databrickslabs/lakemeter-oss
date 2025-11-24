This is a [Next.js](https://nextjs.org) project bootstrapped with [`create-next-app`](https://nextjs.org/docs/app/api-reference/cli/create-next-app).

## Getting Started

Install Node.Js
```
brew install node
```

Clone this project and then install dependencies
```
npm install
```

Create an `.env.local` file at the root folder with the following content

```
NEXT_PUBLIC_ANTHROPIC_API_KEY="<ANTHROPIC_API_KEY>"
```

To Do: Make the LLM endpoint configurable to switch between Anthropic, OpenAI, and others

Then, run the development server:

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
# or
bun dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

