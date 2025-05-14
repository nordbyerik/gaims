from abc import ABC, abstractmethod
import random


class Player(ABC):
  def __init__(self,
               name: str,
               company: Company,
               role: str | None,
               seniority_level: str | None,
               last_performance_checkin: str | None,
               individual_bonus_pct: float | None,
               personal_context: float | None,
               team_workload: float | None,
               mbti_type: str | None,
               disc_type: str | None,
               issue_familiarity: float | None,
          ):
    """Generate random player parameters based on the defined ranges and options"""
    self.name = name
    self.company = company
    self.role = role if role else random.choice(["product", "engineering", "sales", "support", "legal",
                          "marketing", "finance", "hr", "operations", "executive"])
    self.seniority_level = seniority_level if seniority_level else random.choice(["entry", "mid-level", "senior", "team_lead", "manager",
                            "director", "VP", "SVP", "C_level", "board"])
    self.last_performance_checkin = last_performance_checkin if last_performance_checkin else random.choice(["outstanding", "exceeds_expectations", "meets_expectations",
                                    "inconsistent", "needs_improvement", "new_hire", "post_promotion",
                                    "pre_review", "on_pip", "returning_from_leave"])
    self.individual_bonus_pct = individual_bonus_pct if individual_bonus_pct else random.uniform(0, 0.25)
    self.personal_context = personal_context if personal_context else random.uniform(-5, 5)
    self.team_workload = team_workload if team_workload else random.uniform(0.7, 1.5)

    # Generate MBTI type
    self.mbti_type = mbti_type if mbti_type else (
        random.choice(["E", "I"]) +
        random.choice(["S", "N"]) +
        random.choice(["T", "F"]) +
        random.choice(["J", "P"])
    )

    # Select primary DISC type
    self.disc_type = random.choice(["D", "I", "S", "C"])

    # Generate issue familiarity
    self.issue_familiarity = random.uniform(0.01, 1)

    self.full_description = self.long_player_context()
    self.public_description = self.short_profile()
    self.agent = Gemini() # send_message maintains state.

  def send_message(self, message: str) -> str:
    p = self.agent.send_message(message)
    return p.strip()

  def long_player_context(self) -> str:
    """
    Generate a natural language explanation of the player's context
    based on their parameters.

    Returns:
        str: An English description of the player's context
    """
    # Role and seniority description
    role_description = f"You are a {self.seniority_level} level {self.role} professional working in this organization: {self.company.description}"

    # Performance context
    if self.last_performance_checkin == "outstanding":
        performance_desc = "Your last performance review was outstanding, placing you among the top performers"
    elif self.last_performance_checkin == "exceeds_expectations":
        performance_desc = "Your last performance review noted that you exceed expectations in your role"
    elif self.last_performance_checkin == "meets_expectations":
        performance_desc = "Your last performance review indicated that you meet all expectations for your position"
    elif self.last_performance_checkin == "inconsistent":
        performance_desc = "Your last performance review noted some inconsistency in your work quality"
    elif self.last_performance_checkin == "needs_improvement":
        performance_desc = "Your last performance review suggested several areas where improvement is needed"
    elif self.last_performance_checkin == "new_hire":
        performance_desc = "You're a new hire and haven't had a formal performance review yet"
    elif self.last_performance_checkin == "post_promotion":
        performance_desc = "You were recently promoted and are still adapting to your new responsibilities"
    elif self.last_performance_checkin == "pre_review":
        performance_desc = "Your annual performance review is coming up soon"
    elif self.last_performance_checkin == "on_pip":
        performance_desc = "You're currently on a performance improvement plan"
    elif self.last_performance_checkin == "returning_from_leave":
        performance_desc = "You've recently returned from extended leave"

    # Bonus target
    bonus_desc = f"Your individual bonus target is {self.individual_bonus_pct * 100:.1f}% of your base salary"

    # Team workload
    if self.team_workload < 0.85:
        workload_desc = "Your team is currently operating with a comfortable workload"
    elif self.team_workload < 1.0:
        workload_desc = "Your team has a moderate workload, with occasional busy periods"
    elif self.team_workload < 1.2:
        workload_desc = "Your team is quite busy, with a heavy but manageable workload"
    else:
        workload_desc = "Your team is extremely overloaded and working at an unsustainable pace"

    # Personal context
    if self.personal_context < -3:
        personal_desc = "Your personal life is extremely challenging right now, creating significant distractions at work"
    elif self.personal_context < -1:
        personal_desc = "You're dealing with some personal difficulties that occasionally affect your work focus"
    elif self.personal_context < 1:
        personal_desc = "Your personal life is relatively stable, neither helping nor hindering your work"
    elif self.personal_context < 3:
        personal_desc = "Your personal life is going well, giving you additional energy for work"
    else:
        personal_desc = "Your personal life is exceptionally positive, providing you with abundant energy and focus"

    # MBTI description
    mbti_descriptions = {
        'E': "extroverted",
        'I': "introverted",
        'S': "detail-oriented",
        'N': "big-picture focused",
        'T': "logical and analytical",
        'F': "empathetic and values-driven",
        'J': "structured and organized",
        'P': "flexible and adaptable"
    }

    mbti_traits = [mbti_descriptions[letter] for letter in self.mbti_type]
    mbti_desc = f"You tend to be {mbti_traits[0]}, {mbti_traits[1]}, {mbti_traits[2]}, and {mbti_traits[3]}"

    # DISC description
    disc_descriptions = {
        'D': "You're direct, decisive, and focused on results and the bottom line",
        'I': "You're influential, enthusiastic, and naturally good at building relationships",
        'S': "You're steady, patient, and value harmony and cooperation",
        'C': "You're conscientious, analytical, and focused on quality and accuracy"
    }
    disc_desc = disc_descriptions[self.disc_type]

    # Issue familiarity
    if self.issue_familiarity < 0.2:
        familiarity_desc = "You have very little familiarity with the current issue"
    elif self.issue_familiarity < 0.4:
        familiarity_desc = "You have basic knowledge about the current issue"
    elif self.issue_familiarity < 0.6:
        familiarity_desc = "You have moderate familiarity with the current issue"
    elif self.issue_familiarity < 0.8:
        familiarity_desc = "You have strong knowledge about the current issue"
    else:
        familiarity_desc = "You're an expert on the current issue"

    # Combine everything into a comprehensive context
    context = f"""
{role_description}. {performance_desc}.

{bonus_desc}. {workload_desc}. {personal_desc}.

Personality traits: {mbti_desc}. {disc_desc}.

Regarding the current situation: {familiarity_desc}.
"""

    return context.strip()

  def short_profile(self) -> str:
    return Gemini().send_message("""
      In 30 words, what would the person below be known for in their organization? Write in a professional 3rd person voice.
      """ + self.long_player_context())

  def observe_orient_decide_progress(self, message: str, time: str, coworker_name: str) -> float:
    OOD_TEMPLATE = """
    Reply from {coworker_name} after {time}: {reply}.
    First you are observing and reflecting on this reply - what is your internal dialog or what do you look into and find independently?
    Start every line with "(internal)".
    """
    print(self.agent.send_message(OOD_TEMPLATE.format(reply=message, time=time, coworker_name=coworker_name)))
    progress = self.agent.send_message("How much progress do you think this amounts to on the current issue as a percentage (0-100)? Write only the number, no symbol")
    return float(progress)/100

  def act(self) -> str:
    ACT_TEMPLATE = """
    Having observed and reflected above, how long did this take you? And considering your full context, what would you like to write to {partner}?
    You must write only in this format:
    Me [response_time]:lorem ipsum
    (with a number and 1-letter unit in the brackets, eg [1m])
    """
    response = self.agent.send_message(ACT_TEMPLATE)
    print(response)
    return response
