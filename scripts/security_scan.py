#!/usr/bin/env python3
"""
Comprehensive security scanning script for MediGuard AI.
Runs multiple security tools and generates consolidated reports.
"""

import os
import sys
import json
import subprocess
import argparse
from datetime import datetime
from pathlib import Path
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SecurityScanner:
    """Comprehensive security scanner for the application."""
    
    def __init__(self, output_dir: str = "security-reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.results = {}
    
    def run_bandit(self) -> dict:
        """Run Bandit security linter."""
        logger.info("Running Bandit security scan...")
        
        cmd = [
            "bandit",
            "-r", "src/",
            "-f", "json",
            "-o", str(self.output_dir / f"bandit_{self.timestamp}.json"),
            "--quiet"
        ]
        
        try:
            subprocess.run(cmd, check=True)
            
            # Load results
            with open(self.output_dir / f"bandit_{self.timestamp}.json") as f:
                results = json.load(f)
            
            # Extract summary
            summary = {
                "high": 0,
                "medium": 0,
                "low": 0,
                "issues": results.get("results", [])
            }
            
            for issue in results.get("results", []):
                severity = issue.get("issue_severity", "LOW")
                if severity in summary:
                    summary[severity] += 1
            
            logger.info(f"Bandit completed: {summary['high']} high, {summary['medium']} medium, {summary['low']} low")
            return summary
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Bandit scan failed: {e}")
            return {"error": str(e)}
    
    def run_safety(self) -> dict:
        """Run Safety to check for vulnerable dependencies."""
        logger.info("Running Safety dependency scan...")
        
        cmd = [
            "safety",
            "check",
            "--json",
            "--output", str(self.output_dir / f"safety_{self.timestamp}.json")
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            # Parse results
            if result.stdout:
                vulnerabilities = json.loads(result.stdout)
            else:
                vulnerabilities = []
            
            summary = {
                "vulnerabilities": len(vulnerabilities),
                "details": vulnerabilities
            }
            
            logger.info(f"Safety completed: {summary['vulnerabilities']} vulnerabilities found")
            return summary
            
        except Exception as e:
            logger.error(f"Safety scan failed: {e}")
            return {"error": str(e)}
    
    def run_semgrep(self) -> dict:
        """Run Semgrep for static analysis."""
        logger.info("Running Semgrep static analysis...")
        
        config = "p/security-audit,p/secrets,p/owasp-top-ten"
        output_file = self.output_dir / f"semgrep_{self.timestamp}.json"
        
        cmd = [
            "semgrep",
            "--config", config,
            "--json",
            "--output", str(output_file),
            "src/"
        ]
        
        try:
            subprocess.run(cmd, check=True)
            
            # Load results
            with open(output_file) as f:
                results = json.load(f)
            
            # Extract summary
            findings = results.get("results", [])
            summary = {
                "total_findings": len(findings),
                "by_severity": {},
                "findings": findings[:50]  # Limit to first 50
            }
            
            for finding in findings:
                severity = finding.get("metadata", {}).get("severity", "INFO")
                summary["by_severity"][severity] = summary["by_severity"].get(severity, 0) + 1
            
            logger.info(f"Semgrep completed: {summary['total_findings']} findings")
            return summary
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Semgrep scan failed: {e}")
            return {"error": str(e)}
        except FileNotFoundError:
            logger.warning("Semgrep not installed, skipping...")
            return {"skipped": "Semgrep not installed"}
    
    def run_trivy(self, target: str = "filesystem") -> dict:
        """Run Trivy vulnerability scanner."""
        logger.info(f"Running Trivy scan on {target}...")
        
        output_file = self.output_dir / f"trivy_{target}_{self.timestamp}.json"
        
        if target == "filesystem":
            cmd = [
                "trivy",
                "fs",
                "--format", "json",
                "--output", str(output_file),
                "--quiet",
                "src/"
            ]
        elif target == "container":
            # Build image first
            subprocess.run(["docker", "build", "-t", "mediguard:scan", "."], check=True)
            cmd = [
                "trivy",
                "image",
                "--format", "json",
                "--output", str(output_file),
                "--quiet",
                "mediguard:scan"
            ]
        else:
            return {"error": f"Unknown target: {target}"}
        
        try:
            subprocess.run(cmd, check=True)
            
            # Load results
            with open(output_file) as f:
                results = json.load(f)
            
            # Extract summary
            vulnerabilities = results.get("Results", [])
            summary = {
                "vulnerabilities": 0,
                "by_severity": {},
                "details": vulnerabilities
            }
            
            for result in vulnerabilities:
                for vuln in result.get("Vulnerabilities", []):
                    severity = vuln.get("Severity", "UNKNOWN")
                    summary["by_severity"][severity] = summary["by_severity"].get(severity, 0) + 1
                    summary["vulnerabilities"] += 1
            
            logger.info(f"Trivy completed: {summary['vulnerabilities']} vulnerabilities")
            return summary
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Trivy scan failed: {e}")
            return {"error": str(e)}
        except FileNotFoundError:
            logger.warning("Trivy not installed, skipping...")
            return {"skipped": "Trivy not installed"}
    
    def run_gitleaks(self) -> dict:
        """Run Gitleaks to detect secrets in repository."""
        logger.info("Running Gitleaks secret detection...")
        
        output_file = self.output_dir / f"gitleaks_{self.timestamp}.json"
        
        cmd = [
            "gitleaks",
            "detect",
            "--source", ".",
            "--report-format", "json",
            "--report-path", str(output_file),
            "--verbose"
        ]
        
        try:
            subprocess.run(cmd, check=True)
            
            # Load results
            with open(output_file) as f:
                results = json.load(f)
            
            findings = results.get("findings", [])
            summary = {
                "secrets_found": len(findings),
                "findings": findings
            }
            
            if summary["secrets_found"] > 0:
                logger.warning(f"Gitleaks found {summary['secrets_found']} potential secrets!")
            else:
                logger.info("Gitleaks: No secrets found")
            
            return summary
            
        except subprocess.CalledProcessError as e:
            # Gitleaks returns non-zero if secrets are found
            if e.returncode == 1:
                # Load results anyway
                try:
                    with open(output_file) as f:
                        results = json.load(f)
                    findings = results.get("findings", [])
                    return {
                        "secrets_found": len(findings),
                        "findings": findings
                    }
                except:
                    pass
            
            logger.error(f"Gitleaks scan failed: {e}")
            return {"error": str(e)}
        except FileNotFoundError:
            logger.warning("Gitleaks not installed, skipping...")
            return {"skipped": "Gitleaks not installed"}
    
    def run_hipaa_compliance_check(self) -> dict:
        """Run custom HIPAA compliance checks."""
        logger.info("Running HIPAA compliance checks...")
        
        violations = []
        
        # Check for hardcoded credentials
        import re
        credential_pattern = re.compile(
            r"(password|secret|key|token|api_key|private_key)\s*[:=]\s*['\"][^'\"]{8,}['\"]",
            re.IGNORECASE
        )
        
        # Check source files
        for py_file in Path("src").rglob("*.py"):
            try:
                content = py_file.read_text()
                matches = credential_pattern.finditer(content)
                for match in matches:
                    violations.append({
                        "type": "hardcoded_credential",
                        "file": str(py_file),
                        "line": content[:match.start()].count('\n') + 1,
                        "match": match.group()
                    })
            except:
                pass
        
        # Check for PHI patterns
        phi_patterns = [
            (r"\b\d{3}-\d{2}-\d{4}\b", "ssn"),
            (r"\b\d{10}\b", "phone_number"),
            (r"\b\d{3}-\d{3}-\d{4}\b", "us_phone"),
        ]
        
        for pattern, phi_type in phi_patterns:
            regex = re.compile(pattern)
            for py_file in Path("src").rglob("*.py"):
                try:
                    content = py_file.read_text()
                    matches = regex.finditer(content)
                    for match in matches:
                        violations.append({
                            "type": f"potential_phi_{phi_type}",
                            "file": str(py_file),
                            "line": content[:match.start()].count('\n') + 1,
                            "match": match.group()
                        })
                except:
                    pass
        
        summary = {
            "violations": len(violations),
            "findings": violations
        }
        
        if summary["violations"] > 0:
            logger.warning(f"HIPAA check found {summary['violations']} potential violations")
        else:
            logger.info("HIPAA check passed")
        
        return summary
    
    def generate_report(self) -> str:
        """Generate consolidated security report."""
        report_file = self.output_dir / f"security_report_{self.timestamp}.html"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>MediGuard AI Security Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background: #2c3e50; color: white; padding: 20px; }}
                .section {{ margin: 20px 0; padding: 15px; border: 1px solid #ddd; }}
                .high {{ border-left: 5px solid #e74c3c; }}
                .medium {{ border-left: 5px solid #f39c12; }}
                .low {{ border-left: 5px solid #f1c40f; }}
                .pass {{ border-left: 5px solid #27ae60; }}
                table {{ width: 100%; border-collapse: collapse; }}
                th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
                th {{ background: #f5f5f5; }}
                .summary {{ display: flex; gap: 20px; margin: 20px 0; }}
                .metric {{ flex: 1; padding: 15px; background: #f8f9fa; border-radius: 5px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>MediGuard AI Security Report</h1>
                <p>Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
            
            <div class="summary">
                <div class="metric">
                    <h3>Bandit Issues</h3>
                    <p>{self.results.get('bandit', {}).get('high', 0)} High</p>
                    <p>{self.results.get('bandit', {}).get('medium', 0)} Medium</p>
                    <p>{self.results.get('bandit', {}).get('low', 0)} Low</p>
                </div>
                <div class="metric">
                    <h3>Safety</h3>
                    <p>{self.results.get('safety', {}).get('vulnerabilities', 0)} Vulnerabilities</p>
                </div>
                <div class="metric">
                    <h3>Semgrep</h3>
                    <p>{self.results.get('semgrep', {}).get('total_findings', 0)} Findings</p>
                </div>
                <div class="metric">
                    <h3>Trivy</h3>
                    <p>{self.results.get('trivy', {}).get('vulnerabilities', 0)} Vulnerabilities</p>
                </div>
                <div class="metric">
                    <h3>Gitleaks</h3>
                    <p>{self.results.get('gitleaks', {}).get('secrets_found', 0)} Secrets</p>
                </div>
                <div class="metric">
                    <h3>HIPAA</h3>
                    <p>{self.results.get('hipaa', {}).get('violations', 0)} Violations</p>
                </div>
            </div>
            
            <div class="section">
                <h2>Overall Status</h2>
                <p>{self._get_overall_status()}</p>
            </div>
            
            <div class="section">
                <h2>Recommendations</h2>
                <ul>
                    {self._get_recommendations()}
                </ul>
            </div>
        </body>
        </html>
        """
        
        with open(report_file, 'w') as f:
            f.write(html_content)
        
        logger.info(f"Security report generated: {report_file}")
        return str(report_file)
    
    def _get_overall_status(self) -> str:
        """Get overall security status."""
        critical_issues = 0
        
        # Count critical issues
        critical_issues += self.results.get('bandit', {}).get('high', 0)
        critical_issues += self.results.get('safety', {}).get('vulnerabilities', 0)
        critical_issues += self.results.get('gitleaks', {}).get('secrets_found', 0)
        critical_issues += self.results.get('hipaa', {}).get('violations', 0)
        
        if critical_issues > 0:
            return f"⚠️ CRITICAL: {critical_issues} critical security issues found!"
        elif self.results.get('trivy', {}).get('vulnerabilities', 0) > 10:
            return "⚠️ WARNING: Multiple vulnerabilities detected in dependencies"
        else:
            return "✅ PASSED: No critical security issues found"
    
    def _get_recommendations(self) -> str:
        """Get security recommendations based on findings."""
        recommendations = []
        
        if self.results.get('bandit', {}).get('high', 0) > 0:
            recommendations.append("<li>Fix high-priority Bandit security issues immediately</li>")
        
        if self.results.get('safety', {}).get('vulnerabilities', 0) > 0:
            recommendations.append("<li>Update vulnerable dependencies using 'pip install --upgrade'</li>")
        
        if self.results.get('gitleaks', {}).get('secrets_found', 0) > 0:
            recommendations.append("<li>Remove all hardcoded secrets and use environment variables</li>")
        
        if self.results.get('hipaa', {}).get('violations', 0) > 0:
            recommendations.append("<li>Review and fix HIPAA compliance violations</li>")
        
        if not recommendations:
            recommendations.append("<li>Continue following security best practices</li>")
        
        return '\n'.join(recommendations)
    
    def run_all_scans(self) -> dict:
        """Run all security scans."""
        logger.info("Starting comprehensive security scan...")
        
        # Run all scanners
        self.results['bandit'] = self.run_bandit()
        self.results['safety'] = self.run_safety()
        self.results['semgrep'] = self.run_semgrep()
        self.results['trivy'] = self.run_trivy('filesystem')
        self.results['gitleaks'] = self.run_gitleaks()
        self.results['hipaa'] = self.run_hipaa_compliance_check()
        
        # Generate report
        report_path = self.generate_report()
        
        # Save consolidated results
        results_file = self.output_dir / f"security_results_{self.timestamp}.json"
        with open(results_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        logger.info(f"Security scan completed. Report: {report_path}")
        return self.results


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Security scanner for MediGuard AI")
    parser.add_argument(
        "--output-dir",
        default="security-reports",
        help="Output directory for reports"
    )
    parser.add_argument(
        "--scan",
        choices=["bandit", "safety", "semgrep", "trivy", "gitleaks", "hipaa", "all"],
        default="all",
        help="Specific scanner to run"
    )
    
    args = parser.parse_args()
    
    scanner = SecurityScanner(args.output_dir)
    
    if args.scan == "all":
        results = scanner.run_all_scans()
    else:
        # Run specific scan
        results = getattr(scanner, f"run_{args.scan}")()
        print(json.dumps(results, indent=2))
    
    # Exit with error code if critical issues found
    critical_issues = (
        results.get('bandit', {}).get('high', 0) +
        results.get('safety', {}).get('vulnerabilities', 0) +
        results.get('gitleaks', {}).get('secrets_found', 0) +
        results.get('hipaa', {}).get('violations', 0)
    )
    
    sys.exit(1 if critical_issues > 0 else 0)


if __name__ == "__main__":
    main()
