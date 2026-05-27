window.SHALLWE_SAMPLE_DATA = {
  exported_at: "2026-05-27T00:00:00Z",
  contacts: [
    {
      id: 1,
      email: "founder@example.com",
      first_name: "Ava",
      last_name: "Chen",
      full_name: "Ava Chen",
      phone: "",
      linkedin: "https://linkedin.com/in/example",
      organization: "Example AI Studio",
      role_title: "Founder",
      professional_category: "Founder",
      city: "London",
      country: "UK",
      mandarin_speaker: 1,
      interests: "agents,product,venture",
      source: "luma",
      notes: "",
      tags: "speaker-prospect",
      created_at: "2026-01-01T10:00:00",
      updated_at: "2026-05-20T10:00:00"
    },
    {
      id: 2,
      email: "researcher@example.com",
      first_name: "Leo",
      last_name: "Wang",
      full_name: "Leo Wang",
      phone: "",
      linkedin: "",
      organization: "Example University",
      role_title: "PhD Researcher",
      professional_category: "Academic Researcher",
      city: "Cambridge",
      country: "UK",
      mandarin_speaker: 1,
      interests: "world models,research,multimodal",
      source: "manual",
      notes: "",
      tags: "",
      created_at: "2026-01-02T10:00:00",
      updated_at: "2026-05-10T10:00:00"
    }
  ],
  events: [
    { id: 1, name: "AI Forum", date: "2026-01-15", description: "Community forum" },
    { id: 2, name: "Vibe Coding Workshop", date: "2026-03-20", description: "Workshop" }
  ],
  attendance: [
    { contact_id: 1, event_id: 1, event_name: "AI Forum", approval_status: "approved", checked_in_at: "2026-01-15T18:00:00", registered_at: "2026-01-05T09:00:00", ticket_name: "General", motivation: "Meet founders building agents", questions_for_speakers: "How do AI startups find distribution?", experience: "Founder using LLMs" },
    { contact_id: 1, event_id: 2, event_name: "Vibe Coding Workshop", approval_status: "approved", checked_in_at: "2026-03-20T18:00:00", registered_at: "2026-03-01T09:00:00", ticket_name: "Workshop", motivation: "Prototype faster", questions_for_speakers: "How to ship with agents?", experience: "Regular User" },
    { contact_id: 2, event_id: 1, event_name: "AI Forum", approval_status: "approved", checked_in_at: "", registered_at: "2026-01-07T09:00:00", ticket_name: "General", motivation: "Research interest", questions_for_speakers: "What is next for world models?", experience: "Academic AI research" }
  ]
};
