import { useState } from 'react';
import { useParams, useSearchParams } from 'react-router-dom';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Alert, AlertDescription } from '../components/ui/alert';
import { AlertCircle } from 'lucide-react';
import StudentsTab from '../components/class-management/StudentsTab';
import AssignmentsTab from '../components/class-management/AssignmentsTab';
import GradesTab from '../components/class-management/GradesTab';

export default function ClassManagement() {
  const { classId } = useParams<{ classId: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const activeTab = searchParams.get('tab') || 'assignments';

  const handleTabChange = (tab: string) => {
    setSearchParams({ tab });
  };

  if (!classId) {
    return (
      <div className="container mx-auto p-6">
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            No class selected. Please select a class to manage.
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold">Class Management</h1>
        <p className="text-lg text-muted-foreground mt-2">
          Manage assignments, students, and grades for <span className="font-semibold">{classId}</span>
        </p>
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={handleTabChange} className="w-full">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="assignments">Assignments</TabsTrigger>
          <TabsTrigger value="students">Students</TabsTrigger>
          <TabsTrigger value="grades">Grades</TabsTrigger>
        </TabsList>

        <TabsContent value="assignments" className="space-y-4">
          <AssignmentsTab classId={classId} />
        </TabsContent>

        <TabsContent value="students" className="space-y-4">
          <StudentsTab classId={classId} />
        </TabsContent>

        <TabsContent value="grades" className="space-y-4">
          <GradesTab classId={classId} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
