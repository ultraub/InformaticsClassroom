import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { apiClient } from '../services/api';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Alert, AlertDescription } from '../components/ui/alert';
import { Label } from '../components/ui/label';
import { AlertCircle, Loader2, ChevronDown, ChevronRight } from 'lucide-react';

interface ClassModulesResponse {
  success: boolean;
  classes: string[];
  class_modules: Record<string, number[]>;
  error?: string;
}

interface StudentBreakdown {
  team: string;
  attempts: number;
  correct: boolean;
}

interface AttemptDetail {
  answer: string;
  correct: boolean;
  datetime: string;
}

interface QuestionSummary {
  question: string;
  total_students: number;
  correct_students: number;
  attempt_count: number;
  avg_attempts: number;
  percent_correct: number;
  student_breakdown: StudentBreakdown[];
  details: Record<string, AttemptDetail[]>;
}

interface PivotTable {
  columns: string[];
  rows: (string | number)[][];
}

interface AnalysisResponse {
  success: boolean;
  module_summary: QuestionSummary[];
  table_correctness: PivotTable;
  table_attempts: PivotTable;
  error?: string;
}

const CURRENT_YEAR = new Date().getFullYear();
const YEARS = Array.from({ length: 5 }, (_, i) => CURRENT_YEAR - i);

export default function AssignmentAnalysis() {
  const [selectedClass, setSelectedClass] = useState<string>('');
  const [selectedModule, setSelectedModule] = useState<string>('');
  const [selectedYear, setSelectedYear] = useState<string>('all');
  const [expandedQuestions, setExpandedQuestions] = useState<Set<string>>(new Set());
  const [expandedStudents, setExpandedStudents] = useState<Set<string>>(new Set());
  const [analysisData, setAnalysisData] = useState<AnalysisResponse | null>(null);

  // Fetch class modules
  const { data: classModulesData, isLoading } = useQuery<ClassModulesResponse>({
    queryKey: ['instructor', 'class-modules'],
    queryFn: async (): Promise<ClassModulesResponse> => {
      const response = await apiClient.get<ClassModulesResponse>('/api/instructor/class-modules');
      if (!response.success) {
        throw new Error(response.error || 'Failed to load classes');
      }
      if ('data' in response && response.data) {
        return response.data;
      }
      return response as ClassModulesResponse;
    },
  });

  // Analyze mutation
  const analyzeMutation = useMutation({
    mutationFn: async () => {
      const response = await apiClient.post<AnalysisResponse>('/api/assignments/analyze', {
        class_name: selectedClass,
        module_number: selectedModule,
        year_filter: selectedYear,
      });
      if (!response.success) {
        throw new Error(response.error || 'Failed to analyze assignment');
      }
      return response;
    },
    onSuccess: (data) => {
      const result = ('data' in data && data.data) ? data.data : data;
      setAnalysisData(result as AnalysisResponse);
    },
  });

  const handleAnalyze = () => {
    if (!selectedClass || !selectedModule) {
      return;
    }
    setAnalysisData(null);
    setExpandedQuestions(new Set());
    setExpandedStudents(new Set());
    analyzeMutation.mutate();
  };

  const toggleQuestion = (questionNum: string) => {
    const newExpanded = new Set(expandedQuestions);
    if (newExpanded.has(questionNum)) {
      newExpanded.delete(questionNum);
    } else {
      newExpanded.add(questionNum);
    }
    setExpandedQuestions(newExpanded);
  };

  const toggleStudent = (key: string) => {
    const newExpanded = new Set(expandedStudents);
    if (newExpanded.has(key)) {
      newExpanded.delete(key);
    } else {
      newExpanded.add(key);
    }
    setExpandedStudents(newExpanded);
  };

  const availableModules = selectedClass && classModulesData?.class_modules[selectedClass]
    ? classModulesData.class_modules[selectedClass].filter(m => m != null).map(m => String(m))
    : [];

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="h-8 w-8 animate-spin" />
        <span className="ml-2 text-lg">Loading...</span>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold">Assignment Analysis</h1>
        <p className="text-lg text-muted-foreground mt-2">
          Analyze student performance by class and module
        </p>
      </div>

      {/* Selection Form */}
      <Card>
        <CardHeader>
          <CardTitle>Select Assignment</CardTitle>
          <CardDescription>
            Choose class, module, and optionally filter by year
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
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
                      Module {module}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Year Selection */}
            <div className="space-y-2">
              <Label htmlFor="year">Year (optional)</Label>
              <Select value={selectedYear || "all"} onValueChange={(value) => setSelectedYear(value === "all" ? "" : value)}>
                <SelectTrigger id="year">
                  <SelectValue placeholder="All Years" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Years</SelectItem>
                  {YEARS.map((year: number) => (
                    <SelectItem key={year} value={year.toString()}>
                      {year}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="flex justify-end">
            <Button
              onClick={handleAnalyze}
              disabled={!selectedClass || !selectedModule || analyzeMutation.isPending}
            >
              {analyzeMutation.isPending ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  Analyzing...
                </>
              ) : (
                'Analyze'
              )}
            </Button>
          </div>

          {analyzeMutation.error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                {analyzeMutation.error instanceof Error
                  ? analyzeMutation.error.message
                  : 'Failed to analyze assignment'}
              </AlertDescription>
            </Alert>
          )}
        </CardContent>
      </Card>

      {/* Analysis Results */}
      {analysisData && (
        <>
          {/* Pivot Tables */}
          <Card>
            <CardHeader>
              <CardTitle>Overall Student Performance</CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Correctness Table */}
              <div>
                <h4 className="text-lg font-semibold mb-3">Correctness & Score</h4>
                <div className="overflow-x-auto">
                  <table className="min-w-full border-collapse border border-gray-300">
                    <thead>
                      <tr className="bg-gray-100">
                        {analysisData.table_correctness.columns.map((col: string, idx: number) => (
                          <th key={idx} className="border border-gray-300 px-4 py-2 text-left font-semibold">
                            {col}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {analysisData.table_correctness.rows.map((row: (string | number)[], rowIdx: number) => (
                        <tr key={rowIdx} className="hover:bg-gray-50">
                          {row.map((cell: string | number, cellIdx: number) => (
                            <td key={cellIdx} className="border border-gray-300 px-4 py-2">
                              {cell}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Attempts Table */}
              <div>
                <h4 className="text-lg font-semibold mb-3">Total Attempts</h4>
                <div className="overflow-x-auto">
                  <table className="min-w-full border-collapse border border-gray-300">
                    <thead>
                      <tr className="bg-gray-100">
                        {analysisData.table_attempts.columns.map((col: string, idx: number) => (
                          <th key={idx} className="border border-gray-300 px-4 py-2 text-left font-semibold">
                            {col}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {analysisData.table_attempts.rows.map((row: (string | number)[], rowIdx: number) => (
                        <tr key={rowIdx} className="hover:bg-gray-50">
                          {row.map((cell: string | number, cellIdx: number) => (
                            <td key={cellIdx} className="border border-gray-300 px-4 py-2">
                              {cell}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Question-by-Question Breakdown */}
          <Card>
            <CardHeader>
              <CardTitle>Question-by-Question Breakdown</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {analysisData.module_summary.map((question: QuestionSummary, qIdx: number) => (
                <div key={qIdx} className="border rounded-lg">
                  <button
                    onClick={() => toggleQuestion(question.question)}
                    className="w-full px-4 py-3 text-left hover:bg-gray-50 flex items-center justify-between"
                  >
                    <span className="font-medium">
                      Question {question.question} - {question.percent_correct}% Correct, Avg
                      Attempts: {question.avg_attempts}
                    </span>
                    {expandedQuestions.has(question.question) ? (
                      <ChevronDown className="h-5 w-5" />
                    ) : (
                      <ChevronRight className="h-5 w-5" />
                    )}
                  </button>

                  {expandedQuestions.has(question.question) && (
                    <div className="px-4 py-3 border-t bg-gray-50">
                      <p className="text-sm mb-4">
                        <strong>Correct Students:</strong> {question.correct_students} /{' '}
                        <strong>Total Students:</strong> {question.total_students}
                        <br />
                        <strong>Attempt Count:</strong> {question.attempt_count}
                      </p>

                      <h5 className="font-semibold mb-2">Student Breakdown:</h5>
                      <div className="space-y-2">
                        {question.student_breakdown.map((st: StudentBreakdown, sIdx: number) => {
                          const studentKey = `${qIdx}-${sIdx}`;
                          return (
                            <div key={sIdx} className="border rounded">
                              <button
                                onClick={() => toggleStudent(studentKey)}
                                className={`w-full px-3 py-2 text-left text-sm flex items-center justify-between ${
                                  st.correct
                                    ? 'bg-green-100 hover:bg-green-200'
                                    : 'bg-red-100 hover:bg-red-200'
                                }`}
                              >
                                <span>
                                  {st.team} - {st.attempts} attempts,{' '}
                                  {st.correct ? 'Correct' : 'Incorrect'}
                                </span>
                                {expandedStudents.has(studentKey) ? (
                                  <ChevronDown className="h-4 w-4" />
                                ) : (
                                  <ChevronRight className="h-4 w-4" />
                                )}
                              </button>

                              {expandedStudents.has(studentKey) && (
                                <div className="p-3 border-t">
                                  <table className="min-w-full text-sm">
                                    <thead>
                                      <tr className="border-b">
                                        <th className="text-left py-1">Answer</th>
                                        <th className="text-left py-1">Correct</th>
                                        <th className="text-left py-1">Datetime</th>
                                      </tr>
                                    </thead>
                                    <tbody>
                                      {(question.details[st.team] || []).map(
                                        (attempt: AttemptDetail, aIdx: number) => (
                                          <tr key={aIdx} className="border-b last:border-0">
                                            <td className="py-1">{attempt.answer}</td>
                                            <td className="py-1">{attempt.correct ? 'Yes' : 'No'}</td>
                                            <td className="py-1">
                                              {attempt.datetime
                                                ? new Date(attempt.datetime).toLocaleString()
                                                : ''}
                                            </td>
                                          </tr>
                                        )
                                      )}
                                    </tbody>
                                  </table>
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
