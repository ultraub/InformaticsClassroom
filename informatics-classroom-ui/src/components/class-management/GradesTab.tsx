import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../services/api';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Alert, AlertDescription } from '../ui/alert';
import { AlertCircle, Loader2, GraduationCap, Download } from 'lucide-react';

interface Quiz {
  id: string;
  module: number;
  title: string;
  question_count: number;
}

interface GradeDetail {
  score: number;
  total: number;
  percentage: number;
  submitted: boolean;
}

interface GradesData {
  success: boolean;
  students: string[];
  quizzes: Quiz[];
  grades: Record<string, Record<string, GradeDetail>>;
  error?: string;
}

interface GradesTabProps {
  classId: string;
}

export default function GradesTab({ classId }: GradesTabProps) {
  // Fetch grades for this class
  const {
    data: gradesData,
    isLoading: loadingGrades,
    error: gradesError,
  } = useQuery<GradesData>({
    queryKey: ['class', 'grades', classId],
    queryFn: async (): Promise<GradesData> => {
      if (!classId) return { success: false, students: [], quizzes: [], grades: {}, error: 'No class selected' };
      const response = await apiClient.get<GradesData>(`/api/classes/${classId}/grades`);
      return response;
    },
    enabled: !!classId,
  });

  const students = gradesData?.students || [];
  const quizzes = gradesData?.quizzes || [];
  const grades = gradesData?.grades || {};

  // Group quizzes by module
  const quizzesByModule = quizzes.reduce((acc, quiz) => {
    const module = quiz.module ?? 0;
    if (!acc[module]) {
      acc[module] = [];
    }
    acc[module].push(quiz);
    return acc;
  }, {} as Record<number, Quiz[]>);

  // Get color class based on percentage
  const getGradeColor = (percentage: number, submitted: boolean) => {
    if (!submitted) return 'bg-gray-100 text-gray-400';
    if (percentage >= 90) return 'bg-green-100 text-green-800';
    if (percentage >= 80) return 'bg-green-50 text-green-700';
    if (percentage >= 70) return 'bg-yellow-100 text-yellow-800';
    if (percentage >= 60) return 'bg-orange-100 text-orange-800';
    return 'bg-red-100 text-red-800';
  };

  const handleExportCSV = () => {
    if (!gradesData || students.length === 0) {
      return;
    }

    // Build CSV content
    const csvRows: string[] = [];

    // Header row: Student, Quiz1, Quiz2, ..., Average
    const headers = ['Student'];
    const sortedQuizzes = quizzes.sort((a, b) => (a.module || 0) - (b.module || 0));
    sortedQuizzes.forEach((quiz) => {
      headers.push(`Module ${quiz.module} - ${quiz.title}`);
    });
    headers.push('Average');
    csvRows.push(headers.join(','));

    // Data rows: one per student
    students.forEach((student) => {
      const row = [student];
      const studentGrades: number[] = [];

      sortedQuizzes.forEach((quiz) => {
        const gradeDetail = grades[student]?.[quiz.id];
        if (gradeDetail?.submitted) {
          row.push(gradeDetail.percentage.toString());
          studentGrades.push(gradeDetail.percentage);
        } else {
          row.push('—');
        }
      });

      // Calculate average (only for submitted assignments)
      const average =
        studentGrades.length > 0
          ? (studentGrades.reduce((sum, g) => sum + g, 0) / studentGrades.length).toFixed(1)
          : '—';
      row.push(average);

      csvRows.push(row.join(','));
    });

    // Create CSV file and trigger download
    const csvContent = csvRows.join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);

    link.setAttribute('href', url);
    link.setAttribute('download', `${classId}_grades_${new Date().toISOString().split('T')[0]}.csv`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // Calculate class statistics
  const calculateStatistics = () => {
    if (students.length === 0 || quizzes.length === 0) {
      return {
        classAverage: 0,
        completionRate: 0,
        gradeDistribution: { A: 0, B: 0, C: 0, D: 0, F: 0 },
      };
    }

    let totalGrades = 0;
    let totalSubmissions = 0;
    let totalPossibleSubmissions = students.length * quizzes.length;
    const gradeDistribution = { A: 0, B: 0, C: 0, D: 0, F: 0 };

    students.forEach((student) => {
      let studentTotal = 0;
      let studentCount = 0;

      quizzes.forEach((quiz) => {
        const gradeDetail = grades[student]?.[quiz.id];
        if (gradeDetail?.submitted) {
          studentTotal += gradeDetail.percentage;
          studentCount++;
          totalSubmissions++;
        }
      });

      if (studentCount > 0) {
        const studentAverage = studentTotal / studentCount;
        totalGrades += studentAverage;

        // Categorize grade
        if (studentAverage >= 90) gradeDistribution.A++;
        else if (studentAverage >= 80) gradeDistribution.B++;
        else if (studentAverage >= 70) gradeDistribution.C++;
        else if (studentAverage >= 60) gradeDistribution.D++;
        else gradeDistribution.F++;
      }
    });

    const classAverage = students.length > 0 ? totalGrades / students.length : 0;
    const completionRate = (totalSubmissions / totalPossibleSubmissions) * 100;

    return { classAverage, completionRate, gradeDistribution };
  };

  const stats = calculateStatistics();

  return (
    <>
      {/* Error Display */}
      {gradesError && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            {gradesError instanceof Error ? gradesError.message : 'Failed to load grades'}
          </AlertDescription>
        </Alert>
      )}

      {/* Statistics Summary */}
      {!loadingGrades && students.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="pb-3">
              <CardDescription>Class Average</CardDescription>
              <CardTitle className="text-3xl">{stats.classAverage.toFixed(1)}%</CardTitle>
            </CardHeader>
          </Card>
          <Card>
            <CardHeader className="pb-3">
              <CardDescription>Completion Rate</CardDescription>
              <CardTitle className="text-3xl">{stats.completionRate.toFixed(0)}%</CardTitle>
            </CardHeader>
          </Card>
          <Card>
            <CardHeader className="pb-3">
              <CardDescription>Grade Distribution</CardDescription>
              <div className="flex gap-2 mt-2 text-sm">
                <span className="text-green-600">A: {stats.gradeDistribution.A}</span>
                <span className="text-blue-600">B: {stats.gradeDistribution.B}</span>
                <span className="text-yellow-600">C: {stats.gradeDistribution.C}</span>
                <span className="text-orange-600">D: {stats.gradeDistribution.D}</span>
                <span className="text-red-600">F: {stats.gradeDistribution.F}</span>
              </div>
            </CardHeader>
          </Card>
          <Card>
            <CardHeader className="pb-3">
              <CardDescription>Total Assignments</CardDescription>
              <CardTitle className="text-3xl">{quizzes.length}</CardTitle>
            </CardHeader>
          </Card>
        </div>
      )}

      {/* Grades Card */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <GraduationCap className="w-5 h-5" />
                Grades
              </CardTitle>
              <CardDescription>
                {loadingGrades
                  ? 'Loading...'
                  : `${students.length} student(s) • ${quizzes.length} assignment(s)`}
              </CardDescription>
            </div>
            <div className="flex items-center gap-2">
              <Button onClick={handleExportCSV} variant="outline">
                <Download className="w-4 h-4 mr-2" />
                Export CSV
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {loadingGrades ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin" />
              <span className="ml-2 text-lg">Loading grades...</span>
            </div>
          ) : students.length === 0 ? (
            <div className="text-center py-12">
              <GraduationCap className="w-12 h-12 mx-auto text-muted-foreground mb-4" />
              <p className="text-muted-foreground text-lg mb-2">
                No student submissions found yet
              </p>
              <p className="text-sm text-muted-foreground">
                Grades will appear here once students start submitting assignments.
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <div className="min-w-full inline-block align-middle">
                <div className="border rounded-lg overflow-hidden">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th
                          scope="col"
                          className="sticky left-0 z-10 bg-gray-50 px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider border-r"
                        >
                          Student
                        </th>
                        {Object.entries(quizzesByModule)
                          .sort(([a], [b]) => parseInt(a) - parseInt(b))
                          .map(([module, moduleQuizzes]) => (
                            <th
                              key={`module-${module}`}
                              colSpan={moduleQuizzes.length}
                              className="px-4 py-2 text-center text-xs font-semibold text-gray-700 uppercase tracking-wider bg-gray-100 border-l border-r"
                            >
                              Module {module}
                            </th>
                          ))}
                      </tr>
                      <tr>
                        <th className="sticky left-0 z-10 bg-gray-50 border-r"></th>
                        {Object.entries(quizzesByModule)
                          .sort(([a], [b]) => parseInt(a) - parseInt(b))
                          .map(([module, moduleQuizzes]) =>
                            moduleQuizzes.map((quiz, idx) => (
                              <th
                                key={quiz.id}
                                scope="col"
                                className={`px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider ${
                                  idx === 0 ? 'border-l' : ''
                                }`}
                                title={quiz.title}
                              >
                                <div className="flex flex-col">
                                  <span className="truncate max-w-[120px]">{quiz.title}</span>
                                  <span className="text-xs text-gray-400 font-normal">
                                    ({quiz.question_count}q)
                                  </span>
                                </div>
                              </th>
                            ))
                          )}
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {students.map((student) => (
                        <tr key={student} className="hover:bg-gray-50">
                          <td className="sticky left-0 z-10 bg-white px-4 py-3 whitespace-nowrap text-sm font-medium text-gray-900 border-r">
                            {student}
                          </td>
                          {Object.entries(quizzesByModule)
                            .sort(([a], [b]) => parseInt(a) - parseInt(b))
                            .map(([module, moduleQuizzes]) =>
                              moduleQuizzes.map((quiz, idx) => {
                                const gradeDetail = grades[student]?.[quiz.id];
                                const percentage = gradeDetail?.percentage ?? 0;
                                const submitted = gradeDetail?.submitted ?? false;
                                const score = gradeDetail?.score ?? 0;
                                const total = gradeDetail?.total ?? quiz.question_count;

                                return (
                                  <td
                                    key={quiz.id}
                                    className={`px-4 py-3 whitespace-nowrap text-sm ${
                                      idx === 0 ? 'border-l' : ''
                                    }`}
                                  >
                                    <div
                                      className={`inline-flex items-center justify-center px-3 py-1 rounded-md font-medium ${getGradeColor(
                                        percentage,
                                        submitted
                                      )}`}
                                      title={
                                        submitted
                                          ? `${score}/${total} correct (${percentage}%)`
                                          : 'Not submitted'
                                      }
                                    >
                                      {submitted ? (
                                        <>
                                          <span className="font-semibold">{percentage}%</span>
                                          <span className="ml-1 text-xs opacity-75">
                                            ({score}/{total})
                                          </span>
                                        </>
                                      ) : (
                                        <span className="text-xs">—</span>
                                      )}
                                    </div>
                                  </td>
                                );
                              })
                            )}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Legend */}
              <div className="mt-4 flex items-center gap-4 text-xs text-gray-600">
                <span className="font-medium">Grade Scale:</span>
                <div className="flex items-center gap-1">
                  <div className="w-4 h-4 rounded bg-green-100 border border-green-200"></div>
                  <span>90-100%</span>
                </div>
                <div className="flex items-center gap-1">
                  <div className="w-4 h-4 rounded bg-green-50 border border-green-100"></div>
                  <span>80-89%</span>
                </div>
                <div className="flex items-center gap-1">
                  <div className="w-4 h-4 rounded bg-yellow-100 border border-yellow-200"></div>
                  <span>70-79%</span>
                </div>
                <div className="flex items-center gap-1">
                  <div className="w-4 h-4 rounded bg-orange-100 border border-orange-200"></div>
                  <span>60-69%</span>
                </div>
                <div className="flex items-center gap-1">
                  <div className="w-4 h-4 rounded bg-red-100 border border-red-200"></div>
                  <span>&lt;60%</span>
                </div>
                <div className="flex items-center gap-1">
                  <div className="w-4 h-4 rounded bg-gray-100 border border-gray-200"></div>
                  <span>Not submitted</span>
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </>
  );
}
