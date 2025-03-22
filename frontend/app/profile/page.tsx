"use client"

import { useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Edit, User, Calendar, Brain, Clock } from "lucide-react"
import Image from "next/image"
import { Navbar } from "@/components/navbar"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"

export default function ProfilePage() {
  const router = useRouter()

  return (
    <div className="min-h-screen bg-background">
      <Navbar />

      <main className="container py-8">
        <div className="max-w-4xl mx-auto">
          <Card className="border-0 shadow-lg overflow-hidden mb-8">
            <div className="h-32 bg-gradient-to-r from-primary/20 to-primary/10 relative">
              <div className="absolute -bottom-16 left-8">
                <div className="h-32 w-32 rounded-full border-4 border-background overflow-hidden bg-muted">
                  <Image
                    src="/placeholder.svg?height=128&width=128"
                    alt="Profile"
                    width={128}
                    height={128}
                    className="object-cover"
                  />
                </div>
              </div>
            </div>

            <CardContent className="pt-20 pb-6 px-8">
              <div className="flex justify-between items-start">
                <div>
                  <h2 className="text-2xl font-bold">Alfred Mitchell</h2>
                  <div className="text-muted-foreground space-y-1 mt-1">
                    <p>Born: January 15, 1938</p>
                    <p>Diagnosis: Mild Cognitive Impairment</p>
                  </div>
                </div>

                <Button variant="outline" className="flex items-center gap-2">
                  <Edit className="h-4 w-4" />
                  Edit Profile
                </Button>
              </div>
            </CardContent>
          </Card>

          <Tabs defaultValue="progress" className="space-y-6">
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="progress">Progress</TabsTrigger>
              <TabsTrigger value="memories">Memories</TabsTrigger>
              <TabsTrigger value="settings">Settings</TabsTrigger>
            </TabsList>

            <TabsContent value="progress" className="space-y-6">
              <Card className="border-0 shadow-md">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Brain className="h-5 w-5 text-primary" />
                    Daily Progress
                  </CardTitle>
                </CardHeader>
                <CardContent className="p-6 space-y-6">
                  <div>
                    <div className="flex justify-between text-sm mb-2">
                      <span>Daily Questions Completed</span>
                      <span className="font-medium">2/6</span>
                    </div>
                    <div className="h-3 bg-muted rounded-full overflow-hidden">
                      <div className="h-full bg-primary w-1/3 rounded-full"></div>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <Card className="border border-border/50">
                      <CardContent className="p-4 flex flex-col items-center">
                        <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center mb-2">
                          <Brain className="h-6 w-6 text-primary" />
                        </div>
                        <span className="text-2xl font-bold">75%</span>
                        <span className="text-sm text-muted-foreground">Memory Score</span>
                      </CardContent>
                    </Card>

                    <Card className="border border-border/50">
                      <CardContent className="p-4 flex flex-col items-center">
                        <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center mb-2">
                          <Clock className="h-6 w-6 text-primary" />
                        </div>
                        <span className="text-2xl font-bold">90%</span>
                        <span className="text-sm text-muted-foreground">Medication Adherence</span>
                      </CardContent>
                    </Card>
                  </div>
                </CardContent>
              </Card>

              <Card className="border-0 shadow-md">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Calendar className="h-5 w-5 text-primary" />
                    Recent Activity
                  </CardTitle>
                </CardHeader>
                <CardContent className="p-6">
                  <div className="space-y-4">
                    {[
                      { title: "Completed Memory Quiz", time: "Today, 9:30 AM", score: "4/5" },
                      { title: "Medication Reminder", time: "Yesterday, 2:00 PM", score: "Completed" },
                      { title: "Voice Conversation", time: "Yesterday, 10:15 AM", score: "5 mins" },
                    ].map((activity, index) => (
                      <div key={index} className="flex items-center justify-between py-2 border-b last:border-0">
                        <div>
                          <h4 className="font-medium">{activity.title}</h4>
                          <p className="text-sm text-muted-foreground">{activity.time}</p>
                        </div>
                        <span className="text-sm font-medium">{activity.score}</span>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="memories" className="space-y-6">
              <Card className="border-0 shadow-md">
                <CardHeader>
                  <CardTitle>Memory Collections</CardTitle>
                </CardHeader>
                <CardContent className="p-6">
                  <div className="grid grid-cols-2 gap-4">
                    {["Family", "Vacations", "Childhood", "Career"].map((category) => (
                      <Card
                        key={category}
                        className="cursor-pointer hover:shadow-md transition-shadow border border-border/50"
                      >
                        <CardContent className="p-4 flex items-center space-x-4">
                          <div className="h-16 w-16 rounded-md bg-muted flex items-center justify-center">
                            <Image
                              src="/placeholder.svg?height=64&width=64"
                              alt={category}
                              width={64}
                              height={64}
                              className="object-cover rounded-md"
                            />
                          </div>
                          <div>
                            <h3 className="font-medium text-lg">{category}</h3>
                            <p className="text-sm text-muted-foreground">
                              {category === "Family"
                                ? "12 memories"
                                : category === "Vacations"
                                  ? "8 memories"
                                  : category === "Childhood"
                                    ? "15 memories"
                                    : "10 memories"}
                            </p>
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="settings" className="space-y-6">
              <Card className="border-0 shadow-md">
                <CardHeader>
                  <CardTitle>Account Settings</CardTitle>
                </CardHeader>
                <CardContent className="p-6">
                  <p className="text-muted-foreground mb-4">Manage your account settings and preferences</p>

                  <div className="space-y-4">
                    <Button variant="outline" className="w-full justify-start">
                      <User className="mr-2 h-4 w-4" />
                      Personal Information
                    </Button>
                    <Button variant="outline" className="w-full justify-start">
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        width="24"
                        height="24"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        className="mr-2 h-4 w-4"
                      >
                        <rect width="18" height="11" x="3" y="11" rx="2" ry="2" />
                        <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                      </svg>
                      Privacy & Security
                    </Button>
                    <Button variant="outline" className="w-full justify-start">
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        width="24"
                        height="24"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        className="mr-2 h-4 w-4"
                      >
                        <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z" />
                        <circle cx="12" cy="12" r="3" />
                      </svg>
                      Preferences
                    </Button>
                    <Button variant="outline" className="w-full justify-start text-destructive hover:text-destructive">
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        width="24"
                        height="24"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        className="mr-2 h-4 w-4"
                      >
                        <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
                        <polyline points="16 17 21 12 16 7" />
                        <line x1="21" x2="9" y1="12" y2="12" />
                      </svg>
                      Sign Out
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </div>
      </main>
    </div>
  )
}

