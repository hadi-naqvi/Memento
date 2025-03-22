"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"

export default function LoginPage() {
  const router = useRouter()
  const [username, setUsername] = useState("")
  const [password, setPassword] = useState("")
  const [rememberMe, setRememberMe] = useState(false)

  const handleLogin = (userType: string) => {
    // In a real app, you would validate credentials here
    router.push("/dashboard")
  }

  return (
    <>
          {/* Add the test component here, at the beginning of the return statement */}
    <div className="bg-red-500 text-white p-4 m-4 rounded-lg font-bold">
        Tailwind Test - This should be red with white text
    </div>
    <div className="min-h-screen flex flex-col items-center justify-center p-4 wave-pattern">
      <div className="w-full max-w-md">
        <Card className="border-0 shadow-lg">
          <CardHeader className="space-y-1 text-center">
            <div className="flex justify-center mb-2">
              <div className="rounded-full bg-primary p-2">
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  className="h-6 w-6 text-primary-foreground"
                >
                  <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
                </svg>
              </div>
            </div>
            <CardTitle className="text-3xl font-bold">Memento</CardTitle>
            <CardDescription>Your personal memory assistant</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Tabs defaultValue="patient" className="w-full">
              <TabsList className="grid w-full grid-cols-2">
                <TabsTrigger value="patient">Patient</TabsTrigger>
                <TabsTrigger value="caregiver">Caregiver</TabsTrigger>
              </TabsList>
              <TabsContent value="patient" className="space-y-4 mt-4">
                <div className="space-y-2">
                  <Label htmlFor="username-patient">Username</Label>
                  <Input
                    id="username-patient"
                    placeholder="Enter your username"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <Label htmlFor="password-patient">Password</Label>
                    <a href="#" className="text-sm text-primary hover:underline">
                      Forgot password?
                    </a>
                  </div>
                  <Input
                    id="password-patient"
                    type="password"
                    placeholder="••••••••"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                  />
                </div>
                <div className="flex items-center space-x-2">
                  <Switch id="remember-me-patient" checked={rememberMe} onCheckedChange={setRememberMe} />
                  <Label htmlFor="remember-me-patient">Remember me</Label>
                </div>
                <Button className="w-full" onClick={() => handleLogin("patient")}>
                  Sign in
                </Button>
              </TabsContent>
              <TabsContent value="caregiver" className="space-y-4 mt-4">
                <div className="space-y-2">
                  <Label htmlFor="username-caregiver">Username</Label>
                  <Input
                    id="username-caregiver"
                    placeholder="Enter your username"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <Label htmlFor="password-caregiver">Password</Label>
                    <a href="#" className="text-sm text-primary hover:underline">
                      Forgot password?
                    </a>
                  </div>
                  <Input
                    id="password-caregiver"
                    type="password"
                    placeholder="••••••••"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                  />
                </div>
                <div className="flex items-center space-x-2">
                  <Switch id="remember-me-caregiver" checked={rememberMe} onCheckedChange={setRememberMe} />
                  <Label htmlFor="remember-me-caregiver">Remember me</Label>
                </div>
                <Button className="w-full" onClick={() => handleLogin("caregiver")}>
                  Sign in
                </Button>
              </TabsContent>
            </Tabs>
          </CardContent>
          <CardFooter className="flex flex-col space-y-4">
            <div className="text-center text-sm text-muted-foreground">
              <span>Don't have an account? </span>
              <a href="#" className="text-primary underline-offset-4 hover:underline">
                Contact your healthcare provider
              </a>
            </div>
          </CardFooter>
        </Card>
      </div>
    </div>
  </>)
}

