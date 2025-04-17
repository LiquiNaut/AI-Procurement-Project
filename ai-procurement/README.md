# AI Procurement Application

This application helps users specify products with the assistance of AI.

## Features

- User Authentication (Login/Register)
- AI-assisted product specification
- JSON export of final specifications

## Setup

### Installation

1. Clone the repository
2. Navigate to the project directory
3. Install dependencies:

```bash
npm install
```

### OpenAI API Key Setup

This application uses the OpenAI API for AI functionality. To set up your API key:

1. Sign up for an API key at [OpenAI Platform](https://platform.openai.com/)
2. Navigate to `src/environments/environment.ts`
3. Replace `'YOUR_OPENAI_API_KEY'` with your actual API key:

```typescript
export const environment = {
  production: false,
  openai: {
    apiKey: "YOUR_ACTUAL_API_KEY_HERE",
    apiUrl: "https://api.openai.com/v1/chat/completions",
    model: "gpt-3.5-turbo",
  },
};
```

> **IMPORTANT:** Never commit your API key to version control. The `environment.ts` file is included in `.gitignore` to prevent accidental commits.

### Running the Application

Start the development server:

```bash
ng serve
```

Navigate to `http://localhost:4200/`

## Usage

1. Register or login to access the AI chat
2. Describe the product you want to the AI assistant
3. Answer the AI's questions about features, budget, etc.
4. Review the final product specification
5. Download the specification as JSON if desired

## Production Build

For a production build:

1. Update your API key in `src/environments/environment.prod.ts`
2. Run:

```bash
ng build --configuration=production
```

## Development server

To start a local development server, run:

```bash
ng serve
```

Once the server is running, open your browser and navigate to `http://localhost:4200/`. The application will automatically reload whenever you modify any of the source files.

## Code scaffolding

Angular CLI includes powerful code scaffolding tools. To generate a new component, run:

```bash
ng generate component component-name
```

For a complete list of available schematics (such as `components`, `directives`, or `pipes`), run:

```bash
ng generate --help
```

## Building

To build the project run:

```bash
ng build
```

This will compile your project and store the build artifacts in the `dist/` directory. By default, the production build optimizes your application for performance and speed.

## Running unit tests

To execute unit tests with the [Karma](https://karma-runner.github.io) test runner, use the following command:

```bash
ng test
```

## Running end-to-end tests

For end-to-end (e2e) testing, run:

```bash
ng e2e
```

Angular CLI does not come with an end-to-end testing framework by default. You can choose one that suits your needs.

## Additional Resources

For more information on using the Angular CLI, including detailed command references, visit the [Angular CLI Overview and Command Reference](https://angular.dev/tools/cli) page.
