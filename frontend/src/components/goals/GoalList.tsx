// /src/components/goals/GoalList.tsx

'use client';

import { useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { getGoals, archiveGoal } from '@/redux/slices/goalsSlice';
import { RootState, AppDispatch } from '@/redux/store';
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from '@/components/ui/card';
import { Loader2, Trash2, Zap, Target } from 'lucide-react';

export default function GoalList() {
  const dispatch = useDispatch<AppDispatch>();
  const { goals, loading, error } = useSelector((state: RootState) => state.goals);

  // Fetch goals when the component mounts
  useEffect(() => {
    dispatch(getGoals());
  }, [dispatch]);

  const handleArchive = (goalId: number) => {
    if (confirm("Are you sure you want to archive this goal?")) {
      dispatch(archiveGoal(goalId));
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-40">
        <Loader2 className="mr-2 h-6 w-6 animate-spin" />
        <p>Loading your strategic goals...</p>
      </div>
    );
  }

  if (error) {
    return <p className="text-red-500">Error loading goals: {error}</p>;
  }

  return (
    <div className="space-y-4">
      <h2 className="text-2xl font-semibold flex items-center space-x-2 text-gray-700">
          <Target className="w-6 h-6 text-indigo-600" />
          <span>Your Active Goals ({goals.length})</span>
      </h2>
      
      {goals.length === 0 ? (
        <Card className="p-6 border-dashed text-center">
            <p className="text-gray-500">No active goals found. Start by creating a new one!</p>
        </Card>
      ) : (
        goals.map((goal) => (
          <Card key={goal.id} className="shadow-sm border-l-4" style={{ borderColor: goal.weight >= 8 ? '#4F46E5' : '#D1D5DB' }}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0">
              <CardTitle className="text-lg">{goal.title}</CardTitle>
              <div className="flex items-center space-x-2 text-sm text-gray-500">
                <Zap className="w-4 h-4 text-yellow-600" />
                <span>Priority Weight: **{goal.weight}**</span>
              </div>
            </CardHeader>
            <CardContent className="space-y-2">
              <CardDescription>{goal.description}</CardDescription>
              <div className="flex justify-end pt-2">
                <Button 
                  variant="ghost" 
                  size="sm" 
                  onClick={() => handleArchive(goal.id)}
                  className="text-red-500 hover:text-red-600"
                >
                  <Trash2 className="w-4 h-4 mr-1" />
                  Archive
                </Button>
              </div>
            </CardContent>
          </Card>
        ))
      )}
    </div>
  );
}