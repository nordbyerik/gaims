import random
import time
import numpy as np
from dataclasses import dataclass
from typing import List, Dict, Any, Tuple, Optional, Union


ISSUE_TEMPLATE="""
You are simulating a situation in an organization. To situate the context, consider:
{company_context}

An employee protagonist has been told the following about their character and context:
<employee_profile>
{employee_desc}.
</employee_profile>

Given this context, what you need to simulate now is the issue or request related to {issue_type} that the employee is responsible for addressing (complexity: {issue_complexity}/10).
The employee will need to figure it out after your description, by interfacing with {partner_desc}

Simulate in the second person singular what they should know *at this time* to simulate a {familiarity} understanding of the issue/objective. Begin!
"""

class Company(ABC):
  def __init__(self):
    # Beta distribution for company size to create realistic distribution
    size_modeling = {"min": 10, "max": 10000, "beta_a": 1.4, "beta_b": 3.5}
    self.size = int(np.random.beta(size_modeling["beta_a"], size_modeling["beta_b"]) *
                (size_modeling["max"] - size_modeling["min"]) + size_modeling["min"])

    self.vertical = random.choice(["technology", "healthcare", "finance", "retail", "manufacturing",
                      "education", "government", "media", "energy", "transportation"])
    self.org_model = random.choice(["B2C", "B2B", "B2G", "B2B2C", "marketplace", "platform",
                        "hybrid", "franchise", "consortium", "cooperative"])
    self.process_formality = random.randint(1, 10)
    self.outlook_bullishness = random.uniform(-5, 5)
    self.company_bonus_target = random.uniform(0, 0.25)
    self.issue_complexity = random.randint(1, 10)
    self.issue_type = random.choice(["process_improvement", "incident_response", "customer_escalation",
                        "major_deal", "product_innovation", "regulatory_pressure",
                        "reorganization", "market_expansion", "cost_reduction", "talent_acquisition"])
    self.description = self.describe_company_context()

  def describe_company_context(self) -> str:
    """
    Generate a natural language explanation of the company context
    based on the company parameters.

    Returns:
        str: An English description of the company context
    """
    # Company size and industry description
    if self.size < 50:
        size_desc = f"a small startup with {self.size} employees"
    elif self.size < 200:
        size_desc = f"a growing company with {self.size} employees"
    elif self.size < 1000:
        size_desc = f"a mid-sized company with {self.size} employees"
    elif self.size < 5000:
        size_desc = f"a large enterprise with {self.size} employees"
    else:
        size_desc = f"a major corporation with {self.size} employees"

    # Vertical/industry description
    industry_desc = f"operating in the {self.vertical} industry"

    # Business model description
    model_descriptions = {
        "B2C": "selling directly to consumers",
        "B2B": "providing services to other businesses",
        "B2G": "working primarily with government clients",
        "B2B2C": "selling to businesses who serve consumers",
        "marketplace": "operating a platform connecting buyers and sellers",
        "platform": "providing a technology platform for multiple stakeholders",
        "hybrid": "operating with a mix of business models",
        "franchise": "expanding through franchised locations",
        "consortium": "functioning as a consortium of aligned organizations",
        "cooperative": "structured as a cooperative organization"
    }
    model_desc = model_descriptions.get(self.org_model, f"using a {self.org_model} business model")

    # Process formality
    if self.process_formality <= 3:
        process_desc = "The company culture is highly informal with minimal process and documentation"
    elif self.process_formality <= 5:
        process_desc = "The company has a moderately casual approach to processes and documentation"
    elif self.process_formality <= 7:
        process_desc = "The company follows structured processes with reasonable documentation"
    elif self.process_formality <= 9:
        process_desc = "The company adheres to formal processes with thorough documentation"
    else:
        process_desc = "The company has extremely rigorous processes with comprehensive documentation for everything"

    # Business outlook
    if self.outlook_bullishness < -3:
        outlook_desc = "The business outlook is extremely negative, with major challenges ahead"
    elif self.outlook_bullishness < -1:
        outlook_desc = "The business outlook is concerning, with significant headwinds anticipated"
    elif self.outlook_bullishness < 1:
        outlook_desc = "The business outlook is neutral, with balanced opportunities and challenges"
    elif self.outlook_bullishness < 3:
        outlook_desc = "The business outlook is positive, with good growth opportunities ahead"
    else:
        outlook_desc = "The business outlook is extremely bullish, with exceptional growth expected"

    # Bonus structure
    bonus_desc = f"The company-wide bonus target is {self.company_bonus_target * 100:.1f}% of base salary"

    # Combine everything into a comprehensive context
    context = f"""
Your company is {size_desc}, {industry_desc} and {model_desc}.

{process_desc}. {outlook_desc}. {bonus_desc}.
"""

    return context.strip()



class CorporateGameTheory(ABC):
    """Main game class for corporate scenario simulations"""

    def __init__(self):
      self.company = Company()
      self.player_a = Player("Erin", self.company)
      self.player_b = Player("Sam", self.company)
      self.last_turn = ""
      self.last_reply = ""
      self.issue_description = Gemini().send_message(ISSUE_TEMPLATE.format(
        employee_desc=self.player_a.full_description,
        company_context=self.company.description,
        issue_complexity=self.company.issue_complexity,
        issue_type=self.company.issue_type,
        partner_desc=self.player_b.public_description,
        familiarity=self.player_a.issue_familiarity))
      self.steps=0
      self.context_levels_a=[]
      self.context_levels_b=[]
      self.progress_a=[]
      self.progress_b=[]

    def step(self):
      self.steps+=1
      FIRST_TURN="""
      {player_context}

      {issue}:

      Your options today will primarily be based on partnering with {partner} to address the situation as fully as you can, considering your context.
      About {partner}: {partner_desc}
      First you are observing and reflecting on this situation: what is your internal dialog or what do you look into and find independently?
      Start every line with "(internal)". Begin!
      """

      SECOND_TURN="""
      {player_context}

      {partner} has sent you this message:
      {message}
      What you know about {partner} is this: {partner_desc}
      Now you are observing and reflecting on this situation: what is your internal dialog or what do you look into and find independently?
      Start every line with "(internal)". Begin!
      """
      if self.last_turn == "":
        self.player_a.send_message(FIRST_TURN.format(
            player_context=self.player_a.full_description,
            issue=self.issue_description,
            partner=self.player_b.name,
            partner_desc=self.player_b.public_description
          ))
        self.context_levels_a.append(int(self.player_a.send_message(f"NOW: How much context will you need to share with {self.player_b.name}? reply with a single digit between 0-9")[-1]))
        self.last_reply = self.player_a.act()
        self.player_b.send_message(SECOND_TURN.format(
            player_context=self.player_b.full_description,
            partner=self.player_a.name,
            partner_desc=self.player_a.public_description,
            message=self.last_reply
          ))
        self.context_levels_b.append(int(self.player_b.send_message(f"NOW: How much context should you include in your reply to {self.player_a.name}? reply with a single digit between 0-9")[-1]))
        self.last_reply = self.player_b.act()
        self.last_turn = "b"
      elif self.last_turn == "a":
        self.progress_b.append(self.player_b.observe_orient_decide_progress(self.last_reply, "now", self.player_a.name))
        self.context_levels_b.append(int(self.player_b.send_message(f"NOW: How much context should you add in your reply to {self.player_a.name}? on a scale from 0-9, where 4 is average, lower numbers are terse, higher numbers are increasingly detailed? Write your decision with only a single digit.")))
        self.last_reply = self.player_b.act()
        self.last_turn = "b"
      elif self.last_turn == "b":
        self.progress_a.append(self.player_a.observe_orient_decide_progress(self.last_reply, "now", self.player_b.name))
        self.context_levels_a.append(int(self.player_a.send_message(f"NOW: How much context will you need to add in your reply to {self.player_b.name}? reply with a single digit between 0-9")))
        self.last_reply = self.player_a.act()
        self.last_turn = "a"