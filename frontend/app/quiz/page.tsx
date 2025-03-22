"use client"
import { useRouter } from "next/navigation"
import { VoiceQuiz } from "@/components/voice-quiz"
import { Navbar } from "@/components/navbar"

export default function QuizPage() {
  const router = useRouter()

  return (
    <div className="min-h-screen bg-background">
      <Navbar />

      <main className="container py-8">
        <div className="max-w-3xl mx-auto">
          <div className="mb-8 text-center">
            <h1 className="text-3xl font-bold mb-2">Memory Quiz</h1>
            <p className="text-muted-foreground">Answer the questions using your voice to keep your mind sharp</p>
          </div>

          <VoiceQuiz />
        </div>
      </main>
    </div>
  )
}

