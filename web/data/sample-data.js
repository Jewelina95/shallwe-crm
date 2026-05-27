(function () {
  const people = [
    ["Ava Chen", "Founder", "AI product studio", "agents,product,venture", "Founder"],
    ["Leo Wang", "PhD Researcher", "University AI Lab", "world models,research,multimodal", "Academic Researcher"],
    ["Maya Patel", "Product Lead", "Enterprise AI Team", "agents,product,automation", "Enterprise Professional"],
    ["Daniel Liu", "ML Engineer", "Robotics Startup", "world models,research,agents", "Enterprise Professional"],
    ["Sophie Zhang", "Investor", "Early-stage Fund", "venture,product,community", "Investor"],
    ["Ryan Zhao", "Student", "Imperial College London", "career,vibe coding,agents", "Student"],
    ["Emily Xu", "Community Manager", "AI Founder Network", "community,product,venture", "Other"],
    ["Jason Wu", "CTO", "Automation SaaS", "agents,vibe coding,product", "Founder"],
    ["Nina Huang", "Research Scientist", "Applied AI Lab", "research,multimodal,world models", "Academic Researcher"],
    ["Oliver Smith", "Strategy Consultant", "Digital Transformation Group", "product,automation,community", "Enterprise Professional"],
    ["Iris Lin", "Startup Operator", "AI Education Company", "product,community,career", "Founder"],
    ["Kevin Ma", "Data Scientist", "Fintech AI Team", "agents,research,product", "Enterprise Professional"],
    ["Grace Sun", "Master Student", "UCL", "career,research,vibe coding", "Student"],
    ["Tom Harris", "Engineering Manager", "Developer Tools Company", "vibe coding,agents,product", "Enterprise Professional"],
    ["Yuki Tan", "Founder", "Creative AI Studio", "product,community,agents", "Founder"],
    ["Rachel Li", "AI Policy Analyst", "Technology Think Tank", "research,community,product", "Other"],
    ["Marcus Brown", "Partner", "Venture Capital Fund", "venture,product,community", "Investor"],
    ["Chloe Yang", "Product Manager", "Consumer AI App", "product,agents,community", "Enterprise Professional"],
    ["Ethan Zhao", "PhD Candidate", "Cambridge AI Group", "research,world models,multimodal", "Academic Researcher"],
    ["Vivian Qiao", "Growth Lead", "AI SaaS Startup", "product,community,venture", "Enterprise Professional"],
    ["Noah Kim", "Software Engineer", "AI Infrastructure Team", "vibe coding,agents,research", "Enterprise Professional"],
    ["Serena Guo", "Founder", "Healthcare AI Company", "product,venture,agents", "Founder"],
    ["Henry Evans", "Robotics Researcher", "Embodied AI Lab", "world models,research,agents", "Academic Researcher"],
    ["Alice Zhou", "Design Lead", "AI UX Studio", "product,community,vibe coding", "Enterprise Professional"],
    ["Ben Taylor", "Student Builder", "King's College London", "career,vibe coding,community", "Student"],
    ["Linda He", "Principal Scientist", "Foundation Model Lab", "research,multimodal,agents", "Academic Researcher"],
    ["Max Turner", "Founder", "Agent Workflow Startup", "agents,product,venture", "Founder"],
    ["Celia Deng", "Operations Lead", "AI Community", "community,product,career", "Other"],
    ["Aaron Yu", "Investment Analyst", "Seed Fund", "venture,product,community", "Investor"],
    ["Mia Roberts", "AI Engineer", "Enterprise Automation", "agents,automation,vibe coding", "Enterprise Professional"]
  ];

  const events = [
    { id: 1, name: "ShallWe Tech AI Forum", date: "2026-01-15", description: "AI founder, researcher, and operator forum" },
    { id: 2, name: "Vibe Coding Workshop", date: "2026-03-20", description: "Hands-on AI coding and agent workflow workshop" },
    { id: 3, name: "World Models Salon", date: "2026-04-18", description: "Technical discussion on world models and embodied AI" }
  ];

  const contacts = people.map((p, i) => {
    const id = i + 1;
    const [fullName, role, org, interests, category] = p;
    const [firstName, ...rest] = fullName.split(" ");
    return {
      id,
      email: `demo${String(id).padStart(2, "0")}@example.com`,
      first_name: firstName,
      last_name: rest.join(" "),
      full_name: fullName,
      phone: "",
      linkedin: id % 4 === 0 ? "" : `https://linkedin.com/in/shallwe-demo-${id}`,
      organization: org,
      role_title: role,
      professional_category: category,
      city: id % 3 === 0 ? "Cambridge" : "London",
      country: "UK",
      mandarin_speaker: id % 5 === 0 ? 0 : 1,
      interests,
      source: id % 3 === 0 ? "manual" : "luma",
      notes: "",
      tags: id % 6 === 0 ? "speaker-prospect" : id % 4 === 0 ? "vip" : "",
      created_at: "2026-01-01T10:00:00",
      updated_at: "2026-05-20T10:00:00"
    };
  });

  const attendance = [];
  for (const contact of contacts) {
    const eventSpan = contact.id % 7 === 0 ? [1] : contact.id % 4 === 0 ? [1, 2, 3] : contact.id % 3 === 0 ? [2] : [1, 2];
    for (const eventId of eventSpan) {
      const event = events.find(e => e.id === eventId);
      attendance.push({
        contact_id: contact.id,
        event_id: eventId,
        event_name: event.name,
        approval_status: "approved",
        checked_in_at: contact.id % 5 === 0 ? "" : `${event.date}T18:00:00`,
        registered_at: `2026-0${Math.min(eventId + 1, 5)}-${String((contact.id % 20) + 1).padStart(2, "0")}T09:00:00`,
        ticket_name: eventId === 2 ? "Workshop" : "General",
        motivation: `Interested in ${contact.interests.replaceAll(",", ", ")} and meeting the ShallWe Tech community.`,
        questions_for_speakers: eventId === 3 ? "How will world models change AI products?" : "How do builders turn AI research into useful products?",
        experience: contact.role_title
      });
    }
  }

  window.SHALLWE_SAMPLE_DATA = {
    exported_at: "2026-05-27T00:00:00Z",
    contacts,
    events,
    attendance
  };
})();
