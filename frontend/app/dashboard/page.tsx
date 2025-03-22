"use client"
import { useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Calendar, User, Brain } from "lucide-react"
import { ChatInterface } from "@/components/chat-interface"
import { ReminderCard } from "@/components/reminder-card"
import { Navbar } from "@/components/navbar"

export default function Dashboard() {
  const router = useRouter()

  return (
    <div className="min-h-screen bg-background">
      <Navbar />

      <main className="container py-8 space-y-8">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          <div className="md:col-span-2 space-y-6">
            <Card className="border-0 shadow-md overflow-hidden">
              <CardHeader className="gradient-bg text-white">
                <CardTitle className="text-2xl">Welcome Back</CardTitle>
                <CardDescription className="text-white/80">How can I help you today?</CardDescription>
              </CardHeader>
              <CardContent className="p-6">
                <ChatInterface />
              </CardContent>
            </Card>

            <Card className="border-0 shadow-md">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Calendar className="h-5 w-5 text-primary" />
                  Today's Reminders
                </CardTitle>
              </CardHeader>
              <CardContent className="p-6 grid gap-4">
                <ReminderCard
                  title="10 AM: Dr. Reed Appointment"
                  description="Check your calendar for detailed location and preparation information."
                  imageSrc="/placeholder.svg?height=100&width=100"
                  time="10:00 AM"
                />
                <ReminderCard
                  title="3 PM: Sarah's Visit"
                  description="Sarah is coming over. Prepare some tea and biscuits."
                  imageSrc="/placeholder.svg?height=100&width=100"
                  time="3:00 PM"
                />
              </CardContent>
            </Card>
          </div>

          <div className="space-y-6">
            <Card className="border-0 shadow-md">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Brain className="h-5 w-5 text-primary" />
                  Memory Quiz
                </CardTitle>
              </CardHeader>
              <CardContent className="p-6 text-center">
                <div className="mb-4">
                  <div className="w-24 h-24 rounded-full bg-primary/10 flex items-center justify-center mx-auto mb-4">
                    <Brain className="h-12 w-12 text-primary" />
                  </div>
                  <h3 className="text-lg font-medium">Daily Brain Exercise</h3>
                  <p className="text-muted-foreground mt-2">Keep your mind sharp with our interactive memory quiz</p>
                </div>
                <Button className="w-full" onClick={() => router.push("/quiz")}>
                  Start Quiz
                </Button>
              </CardContent>
            </Card>

            <Card className="border-0 shadow-md">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <User className="h-5 w-5 text-primary" />
                  Profile Summary
                </CardTitle>
              </CardHeader>
              <CardContent className="p-6">
                <div className="flex items-center gap-4 mb-4">
                  <div className="h-16 w-16 rounded-full bg-muted flex-shrink-0 overflow-hidden">
                    <img
                      src="/placeholder.svg?height=64&width=64"
                      alt="Profile"
                      className="h-full w-full object-cover"
                    />
                  </div>
                  <div>
                    <h3 className="font-medium">Alfred Mitchell</h3>
                    <p className="text-sm text-muted-foreground">Born: January 15, 1938</p>
                  </div>
                </div>

                <div className="space-y-3">
                  <div>
                    <div className="flex justify-between text-sm mb-1">
                      <span>Daily Questions</span>
                      <span className="font-medium">2/6 Completed</span>
                    </div>
                    <div className="h-2 bg-muted rounded-full overflow-hidden">
                      <div className="h-full bg-primary w-1/3 rounded-full"></div>
                    </div>
                  </div>

                  <Button variant="outline" className="w-full" onClick={() => router.push("/profile")}>
                    View Profile
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </main>
    </div>
  )
}

