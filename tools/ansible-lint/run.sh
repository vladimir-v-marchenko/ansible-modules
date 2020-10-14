#!/usr/bin/env bash

lint_passed=0
syntax_passed=0
lint_failed=0
syntax_failed=0

[[ -f "~/.bash_profile" ]] &&  source "~/.bash_profile"

for i in "ansible" "ansible-lint"; do
  which $i >/dev/null 2>&1
  exit_code=$?
  if [[ ${exit_code} != 0 ]]; then
     printf "%s command not found" ${i}
  fi
done


#[[ "x$ANSIBLE_DIR" == "x" ]] && export ANSIBLE_DIR="$(pwd)"

git ls-files *.yml | while read playbook_file; do
    printf "\e[0;36m--> Executing Ansible Lint on %s...\e[0m\n" $(realpath $playbook_file)
	ansible-lint $playbook_file
	linter_exit_code=$?
	if [[ "$linter_exit_code" -eq 0 ]]; then
	    printf "\e[0;32mLint completed successfully.\e[0m\n"
      let lint_passed++
	else
	    printf "\e[0;31mLint completed with exit code: %s.\e[0m\n" $linter_exit_code
      let lint_failed++
	fi
      printf "\e[0;36m--> Executing Ansible Playbook syntax check on %s...\e[0m" $(realpath $playbook_file)
	ANSIBLE_DEPRECATION_WARNINGS=False ansible-playbook -i inventory/aws/slave-aws-local $playbook_file --syntax-check -e connection=local -e version=LATEST
	syntax_check_exit_code=$?
        if [[ $syntax_check_exit_code -eq 0 ]]; then
	    printf "\e[0;32mSyntax check completed successfully.\e[0m\n"
      let syntax_passed++
	else
	    printf "\e[0;31mSyntax check completed with exit code: %s.\e[0m\n" $syntax_check_exit_code
      let syntax_failed++
        fi


printf "\n\e[0;36mLinter \e[0;32mpassed: ${lint_passed} \e[0;31mfailed: ${lint_failed} \e[0m\n" > tools/linter_count
printf "\e[0;36mSyntax \e[0;32mpassed: ${syntax_passed} \e[0;31mfailed: ${syntax_failed} \e[0m\n" > tools/syntax_count

done

cat tools/linter_count
cat tools/syntax_count
#   printf "\n\e[0;36mLinter \e[0;32mpassed: ${lint_passed} \e[0;31mfailed: ${lint_failed} \e[0m\n"
#   printf "\e[0;36mSyntax \e[0;32mpassed: ${syntax_passed} \e[0;31mfailed: ${syntax_failed} \e[0m\n"

exit
