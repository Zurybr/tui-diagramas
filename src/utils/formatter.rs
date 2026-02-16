// src/utils/formatter.rs
use serde_json::Value;
use regex::Regex;

pub fn format_json(content: &str, indent: usize) -> Result<String, String> {
    let value: Value = serde_json::from_str(content)
        .map_err(|e| format!("Invalid JSON: {}", e))?;

    let formatter = serde_json::ser::PrettyFormatter::with_indent(b" ".repeat(indent).as_bytes());
    let mut buf = Vec::new();
    let mut serializer = serde_json::Serializer::with_formatter(&mut buf, formatter);

    value.serialize(&mut serializer)
        .map_err(|e| format!("Serialization error: {}", e))?;

    String::from_utf8(buf).map_err(|e| e.to_string())
}

pub fn minify_json(content: &str) -> Result<String, String> {
    let value: Value = serde_json::from_str(content)
        .map_err(|e| format!("Invalid JSON: {}", e))?;
    serde_json::to_string(&value).map_err(|e| e.to_string())
}

pub fn format_ldap(content: &str) -> String {
    // LDAP filter formatting
    // Example: (|(objectClass=user)(objectClass=group)) -> expand
    let mut result = content.to_string();

    // Add newlines after each )
    let re = Regex::new(r"\)").unwrap();
    result = re.replace_all(&result, ")\n").to_string();

    // Indent after |( or &(
    let re = Regex::new(r"\(\|").unwrap();
    result = re.replace_all(&result, "(|").to_string();
    let re = Regex::new(r"\(\&").unwrap();
    result = re.replace_all(&result, "(&").to_string();

    // Format DN (Distinguished Name)
    let re = Regex::new(r",(?=[A-Za-z]=)").unwrap();
    result = re.replace_all(&result, ",\n").to_string();

    result
}

pub fn format_ldap_filter(filter: &str) -> String {
    let mut formatted = String::new();
    let mut indent = 0;
    let mut in_parens = false;

    for ch in filter.chars() {
        match ch {
            '(' => {
                formatted.push(ch);
                in_parens = true;
                indent += 2;
            }
            ')' => {
                indent = indent.saturating_sub(2);
                formatted.push('\n');
                formatted.push_str(&" ".repeat(indent));
                formatted.push(ch);
                in_parens = false;
            }
            '|' | '&' => {
                formatted.push_str("\n  ");
                formatted.push(ch);
            }
            _ => formatted.push(ch),
        }
    }

    formatted
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_format_json() {
        let input = r#"{"name":"test","value":123}"#;
        let result = format_json(input, 2);
        assert!(result.is_ok());
    }

    #[test]
    fn test_format_ldap() {
        let input = "cn=user,ou=users,dc=example,dc=com";
        let result = format_ldap(input);
        assert!(result.contains('\n'));
    }
}
