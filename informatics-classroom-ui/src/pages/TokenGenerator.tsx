import { useState, useEffect } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { apiClient } from '../services/api';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Alert, AlertDescription } from '../components/ui/alert';
import { Label } from '../components/ui/label';
import { Key, Copy, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';

interface ClassModulesResponse {
  success: boolean;
  classes: string[];
  class_modules: Record<string, number[]>;
  error?: string;
}

interface TokenResponse {
  success: boolean;
  token?: string;
  expiry?: string;
  error?: string;
}

export default function TokenGenerator() {
  const [selectedClass, setSelectedClass] = useState<string>('');
  const [selectedModule, setSelectedModule] = useState<string>('');
  const [generatedToken, setGeneratedToken] = useState<string>('');
  const [tokenExpiry, setTokenExpiry] = useState<string>('');
  const [copied, setCopied] = useState<boolean>(false);

  // Fetch class modules data
  const { data: classModulesData, isLoading, error } = useQuery<ClassModulesResponse>({
    queryKey: ['instructor', 'class-modules'],
    queryFn: async (): Promise<ClassModulesResponse> => {
      const response = await apiClient.get<ClassModulesResponse>('/api/instructor/class-modules');
      if (!response.success) {
        throw new Error(response.error || 'Failed to load classes');
      }
      // Unwrap ApiResponse if needed
      if ('data' in response && response.data) {
        return response.data;
      }
      return response as ClassModulesResponse;
    },
  });

  // Reset module when class changes
  useEffect(() => {
    setSelectedModule('');
    setGeneratedToken('');
    setTokenExpiry('');
  }, [selectedClass]);

  // Generate token mutation
  const generateMutation = useMutation({
    mutationFn: async () => {
      const response = await apiClient.post<TokenResponse>('/api/tokens/generate', {
        class_val: selectedClass,
        module_val: selectedModule,
      });
      if (!response.success) {
        throw new Error(response.error || 'Failed to generate token');
      }
      return response;
    },
    onSuccess: (data) => {
      const result = ('data' in data && data.data) ? data.data : data;
      if ('token' in result && result.token) {
        setGeneratedToken(result.token);
        setTokenExpiry(result.expiry || '');
      }
    },
  });

  const handleGenerate = () => {
    if (!selectedClass || !selectedModule) {
      return;
    }
    setGeneratedToken('');
    setTokenExpiry('');
    setCopied(false);
    generateMutation.mutate();
  };

  const handleCopy = async () => {
    if (generatedToken) {
      await navigator.clipboard.writeText(generatedToken);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const formatExpiry = (isoString: string) => {
    try {
      const date = new Date(isoString);
      return date.toLocaleString();
    } catch {
      return isoString;
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="h-8 w-8 animate-spin" />
        <span className="ml-2 text-lg">Loading...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container mx-auto p-6">
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            {error instanceof Error ? error.message : 'Failed to load classes'}
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  const availableModules = selectedClass && classModulesData?.class_modules[selectedClass]
    ? classModulesData.class_modules[selectedClass].filter(m => m != null).map(m => String(m))
    : [];

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold">Generate Personal Access Token</h1>
        <p className="text-lg text-muted-foreground mt-2">
          Create a personal access token for quiz access without full authentication
        </p>
      </div>

      {/* Information Card */}
      <Card className="border-blue-200 bg-blue-50/50">
        <CardHeader>
          <CardTitle className="text-lg">About Personal Access Tokens</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-sm text-muted-foreground">
            <strong>Personal access tokens are tied to your account</strong> and provide temporary quiz access without requiring you to log in each time.
          </p>
          <div className="text-sm space-y-2">
            <p><strong>Important:</strong></p>
            <ul className="list-disc list-inside space-y-1 text-muted-foreground">
              <li>Tokens are personal and specific to your user account</li>
              <li>Each token grants access to one specific class and module</li>
              <li>Tokens expire after 24 hours for security</li>
              <li>Do not share your personal tokens with others</li>
            </ul>
          </div>
          <div className="text-sm space-y-1">
            <p><strong>Token Contents:</strong></p>
            <p className="text-muted-foreground ml-4">Your token will contain: User ID, Class, Module, and Expiry time</p>
          </div>
        </CardContent>
      </Card>

      {/* Token Generation Form */}
      <Card>
        <CardHeader>
          <CardTitle>Generate Token</CardTitle>
          <CardDescription>
            Select a class and module to create a 24-hour access token for students
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Class Selection */}
            <div className="space-y-2">
              <Label htmlFor="class">Class *</Label>
              <Select value={selectedClass || undefined} onValueChange={setSelectedClass}>
                <SelectTrigger id="class">
                  <SelectValue placeholder="Select a class" />
                </SelectTrigger>
                <SelectContent>
                  {classModulesData?.classes.filter(cls => cls && cls.trim() !== '').map((cls: string) => (
                    <SelectItem key={cls} value={cls}>
                      {cls}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Module Selection */}
            <div className="space-y-2">
              <Label htmlFor="module">Module *</Label>
              <Select
                value={selectedModule || undefined}
                onValueChange={setSelectedModule}
                disabled={!selectedClass || availableModules.length === 0}
              >
                <SelectTrigger id="module">
                  <SelectValue placeholder="Select a module" />
                </SelectTrigger>
                <SelectContent>
                  {availableModules.map((module: string) => (
                    <SelectItem key={module} value={String(module)}>
                      {module}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Generate Button */}
          <div className="flex justify-end">
            <Button
              onClick={handleGenerate}
              disabled={!selectedClass || !selectedModule || generateMutation.isPending}
            >
              {generateMutation.isPending ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  Generating...
                </>
              ) : (
                <>
                  <Key className="w-4 h-4 mr-2" />
                  Generate Token
                </>
              )}
            </Button>
          </div>

          {/* Error Display */}
          {generateMutation.error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                {generateMutation.error instanceof Error
                  ? generateMutation.error.message
                  : 'Failed to generate token'}
              </AlertDescription>
            </Alert>
          )}
        </CardContent>
      </Card>

      {/* Generated Token Display */}
      {generatedToken && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <CheckCircle className="w-5 h-5 text-green-600 mr-2" />
              Personal Token Generated
            </CardTitle>
            <CardDescription>
              This token will expire at {formatExpiry(tokenExpiry)}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Token Details */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 p-4 bg-muted/50 rounded-lg">
              <div>
                <Label className="text-xs text-muted-foreground">Class</Label>
                <p className="font-semibold">{selectedClass}</p>
              </div>
              <div>
                <Label className="text-xs text-muted-foreground">Module</Label>
                <p className="font-semibold">{selectedModule}</p>
              </div>
              <div>
                <Label className="text-xs text-muted-foreground">Expires</Label>
                <p className="font-semibold text-sm">{formatExpiry(tokenExpiry)}</p>
              </div>
            </div>

            {/* Token String */}
            <div className="space-y-2">
              <Label>Your Personal Access Token</Label>
              <div className="flex items-center gap-2">
                <div className="flex-1 p-3 bg-muted rounded-md font-mono text-sm break-all">
                  {generatedToken}
                </div>
                <Button onClick={handleCopy} variant="outline" size="sm">
                  {copied ? (
                    <>
                      <CheckCircle className="w-4 h-4 mr-2 text-green-600" />
                      Copied
                    </>
                  ) : (
                    <>
                      <Copy className="w-4 h-4 mr-2" />
                      Copy
                    </>
                  )}
                </Button>
              </div>
            </div>

            <Alert>
              <AlertCircle className="h-4 w-4" />
              <AlertDescription className="space-y-2">
                <p>
                  <strong>Personal Token:</strong> This token is tied to your account and grants you access to{' '}
                  <strong>{selectedClass}</strong> - Module <strong>{selectedModule}</strong>.
                </p>
                <div className="text-sm space-y-1">
                  <p className="text-muted-foreground">
                    • Keep your token secure and do not share it with others
                  </p>
                  <p className="text-muted-foreground">
                    • Use this token URL parameter to access the quiz without logging in
                  </p>
                  <p className="text-muted-foreground">
                    • Token automatically expires in 24 hours
                  </p>
                </div>
              </AlertDescription>
            </Alert>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
