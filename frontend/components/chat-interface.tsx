"use client"

import { useState, useRef, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Mic, MicOff } from "lucide-react"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"

type Message = {
  role: "user" | "assistant"
  content: string
}

// Declare SpeechRecognition type
declare global {
  interface Window {
    SpeechRecognition: SpeechRecognition
    webkitSpeechRecognition: SpeechRecognition
  }
}

export function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content: "How can I help you today?",
    },
  ])
  const [isListening, setIsListening] = useState(false)
  const [transcript, setTranscript] = useState("")
  const recognitionRef = useRef<SpeechRecognition | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (typeof window !== "undefined" && ("SpeechRecognition" in window || "webkitSpeechRecognition" in window)) {
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
      recognitionRef.current = new SpeechRecognition()
      recognitionRef.current.continuous = true
      recognitionRef.current.interimResults = true

      recognitionRef.current.onresult = (event) => {
        const transcript = Array.from(event.results)
          .map((result) => result[0])
          .map((result) => result.transcript)
          .join("")

        setTranscript(transcript)
      }

      recognitionRef.current.onend = () => {
        if (isListening) {
          recognitionRef.current?.start()
        }
      }
    }

    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.stop()
      }
    }
  }, [isListening])

  useEffect(() => {
    scrollToBottom()
  }, [messages, transcript])

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  const toggleListening = () => {
    if (isListening) {
      if (recognitionRef.current) {
        recognitionRef.current.stop()
      }
      if (transcript) {
        handleUserMessage(transcript)
        setTranscript("")
      }
    } else {
      if (recognitionRef.current) {
        recognitionRef.current.start()
      }
    }
    setIsListening(!isListening)
  }

  const handleUserMessage = (text: string) => {
    const userMessage: Message = {
      role: "user",
      content: text,
    }

    setMessages((prev) => [...prev, userMessage])

    // Simulate assistant response
    setTimeout(() => {
      let response = ""

      if (text.toLowerCase().includes("schedule") || text.toLowerCase().includes("today")) {
        response = "You have two appointments today: 10 AM - Dr. Evelyn Reed & 3 PM - Sarah's visit"
      } else if (text.toLowerCase().includes("weather")) {
        response = "It's currently sunny and 72°F outside. Perfect weather for a short walk!"
      } else if (text.toLowerCase().includes("remind") || text.toLowerCase().includes("medication")) {
        response = "I've set a reminder for your medication at 2 PM. I'll notify you when it's time."
      } else {
        response = "I'm here to help with your schedule, reminders, and daily activities. What would you like to know?"
      }

      setMessages((prev) => [...prev, { role: "assistant", content: response }])
    }, 1000)
  }

  return (
    <div className="space-y-4">
      <div className="space-y-4 max-h-[400px] overflow-y-auto pr-2">
        {messages.map((message, index) => (
          <div
            key={index}
            className={`flex items-start gap-3 ${message.role === "user" ? "justify-end" : "justify-start"}`}
          >
            {message.role === "assistant" && (
              <Avatar className="h-8 w-8">
                <AvatarImage src="/placeholder.svg?height=32&width=32" alt="Assistant" />
                <AvatarFallback className="bg-primary text-primary-foreground">M</AvatarFallback>
              </Avatar>
            )}

            <div
              className={`max-w-[80%] rounded-lg p-3 ${
                message.role === "user" ? "bg-primary text-primary-foreground" : "bg-muted"
              }`}
            >
              {message.content}
            </div>

            {message.role === "user" && (
              <Avatar className="h-8 w-8">
                <AvatarImage src="/placeholder.svg?height=32&width=32" alt="User" />
                <AvatarFallback className="bg-secondary">U</AvatarFallback>
              </Avatar>
            )}
          </div>
        ))}

        {isListening && transcript && (
          <div className="flex items-start gap-3 justify-end">
            <div className="max-w-[80%] rounded-lg p-3 bg-primary/20">{transcript}</div>
            <Avatar className="h-8 w-8">
              <AvatarImage src="/placeholder.svg?height=32&width=32" alt="User" />
              <AvatarFallback className="bg-secondary">U</AvatarFallback>
            </Avatar>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <div className="flex justify-center mt-6">
        <Button
          size="lg"
          className={`rounded-full h-16 w-16 p-0 ${isListening ? "recording-animation bg-red-500 hover:bg-red-600" : "speak-button"}`}
          onClick={toggleListening}
        >
          {isListening ? <MicOff className="h-6 w-6 text-white" /> : <Mic className="h-6 w-6 text-white" />}
          <span className="sr-only">{isListening ? "Stop" : "Speak"}</span>
        </Button>
      </div>
    </div>
  )
}

