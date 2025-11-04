# Informatics Classroom UI

Modern React-based user interface for the Informatics Classroom permission management system.

## Features

- 🎨 Clean, minimal dashboard design with Tailwind CSS
- 🔐 Comprehensive authentication and authorization
- 👥 Advanced user management with search and filtering
- 🛡️ Visual permission matrix for role management
- 📋 Role templates for quick permission assignment
- 📊 Audit trail viewer for tracking changes
- 📱 Fully responsive mobile-first design
- ♿ Accessible components following WCAG standards

## Tech Stack

- **Framework**: React 18 + TypeScript
- **Build Tool**: Vite
- **Styling**: Tailwind CSS + Headless UI
- **Routing**: React Router v6
- **State Management**: Zustand
- **Server State**: TanStack Query (React Query)
- **HTTP Client**: Axios
- **Icons**: Heroicons

## Prerequisites

- Node.js 18+ and npm
- Python 3.9+ (for Flask backend)

## Getting Started

### 1. Install Dependencies

```bash
npm install
```

### 2. Environment Configuration

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Update the `.env` file with your configuration:

```env
VITE_API_BASE_URL=http://localhost:5000
VITE_APP_NAME=Informatics Classroom
VITE_APP_VERSION=1.0.0
```

### 3. Start Development Server

```bash
npm run dev
```

The application will be available at `http://localhost:5173`

### 4. Backend Setup

Make sure the Flask backend is running on `http://localhost:5000`. See the main project README for backend setup instructions.

## Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run lint` - Run ESLint

## Project Structure

```
src/
├── components/          # React components
│   ├── auth/           # Authentication components
│   ├── common/         # Reusable UI components
│   ├── layout/         # Layout components (Sidebar, Header)
│   ├── permissions/    # Permission management components
│   └── users/          # User management components
├── hooks/              # Custom React hooks
├── pages/              # Page components
├── services/           # API service layer
│   ├── api.ts         # Axios instance and interceptors
│   ├── auth.ts        # Authentication API
│   ├── users.ts       # User management API
│   ├── permissions.ts # Permission management API
│   └── audit.ts       # Audit log API
├── store/              # Zustand stores
│   ├── authStore.ts   # Authentication state
│   └── uiStore.ts     # UI state (sidebar, modals, toasts)
├── types/              # TypeScript type definitions
├── utils/              # Utility functions
├── App.tsx            # Main application component
└── main.tsx           # Application entry point
```

## Key Features Explained

### Authentication Flow

- Session-based authentication with Flask backend
- Automatic token refresh
- Protected routes with role-based access control
- Persistent session storage

### User Management

- Search and filter users by name, role, and status
- Paginated table view with sorting
- Inline editing and deletion
- Bulk operations support

### Permission Management

- Visual permission matrix showing user-permission relationships
- Role templates for quick permission assignment
- Class-specific role assignments
- Granular permission control (20+ permissions)

### Audit Trail

- Comprehensive logging of all permission changes
- Filterable by user, action, date range
- Export functionality for compliance
- Real-time activity monitoring

## Development Guidelines

### Component Structure

- Use functional components with hooks
- Extract reusable logic into custom hooks
- Keep components small and focused
- Use TypeScript for type safety

### Styling

- Use Tailwind utility classes
- Follow the design system defined in `tailwind.config.js`
- Use Headless UI for complex interactive components
- Maintain consistent spacing and colors

### State Management

- Use Zustand for global client state
- Use TanStack Query for server state
- Avoid prop drilling - use context or stores
- Keep state close to where it's used

### API Integration

- All API calls go through service modules
- Use TanStack Query for data fetching
- Handle loading and error states
- Implement optimistic updates where appropriate

## Building for Production

```bash
npm run build
```

The build output will be in the `dist/` directory.

### Flask Integration

To serve the React app from Flask:

1. Build the React app: `npm run build`
2. Copy `dist/` contents to Flask's `static/` directory
3. Update Flask routes to serve `index.html` for all non-API routes

See deployment documentation for detailed instructions.

## Browser Support

- Chrome/Edge (last 2 versions)
- Firefox (last 2 versions)
- Safari (last 2 versions)

## Accessibility

- Semantic HTML
- ARIA labels and roles
- Keyboard navigation support
- Screen reader friendly
- Focus management
- Color contrast compliance

## Contributing

1. Follow the existing code style
2. Write meaningful commit messages
3. Test thoroughly before submitting
4. Update documentation as needed

## License

MIT License - see LICENSE file for details
